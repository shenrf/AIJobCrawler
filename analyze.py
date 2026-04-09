"""Requirements analysis and cross-company comparison for AIJobCrawler."""

import json
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from config import DB_PATH, OUTPUT_DIR
from db import get_connection


def load_requirements(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Load all roles joined with their requirements."""
    rows = conn.execute(
        """SELECT r.id as role_id, r.title, r.team, r.location,
                  c.name as company, c.category,
                  req.min_yoe, req.max_yoe, req.degree_level,
                  req.skills, req.languages,
                  req.publications_expected
           FROM roles r
           JOIN companies c ON r.company_id = c.id
           LEFT JOIN requirements req ON req.role_id = r.id"""
    ).fetchall()
    return [dict(row) for row in rows]


def top_skills(data: list[dict[str, Any]], n: int = 20) -> list[tuple[str, int]]:
    """Return top N most-demanded skills across all roles."""
    counter: Counter[str] = Counter()
    for row in data:
        raw = row.get("skills")
        if not raw:
            continue
        skills = json.loads(raw) if isinstance(raw, str) else raw
        # Count each skill once per role (deduplicate within a role)
        for skill in set(skills):
            counter[skill] += 1
    return counter.most_common(n)


def degree_distribution(data: list[dict[str, Any]]) -> dict[str, int]:
    """Distribution of degree requirements: PhD, MS, BS, not specified."""
    dist: dict[str, int] = {"PhD": 0, "MS": 0, "BS": 0, "Not Specified": 0}
    for row in data:
        degree = row.get("degree_level")
        if degree in dist:
            dist[degree] += 1
        else:
            dist["Not Specified"] += 1
    return dist


def yoe_distribution(data: list[dict[str, Any]]) -> dict[str, int]:
    """Bucket roles by years of experience: 0-2, 3-5, 5-8, 8+, not specified."""
    buckets: dict[str, int] = {
        "0-2": 0, "3-5": 0, "5-8": 0, "8+": 0, "Not Specified": 0
    }
    for row in data:
        min_yoe = row.get("min_yoe")
        if min_yoe is None:
            buckets["Not Specified"] += 1
        elif min_yoe <= 2:
            buckets["0-2"] += 1
        elif min_yoe <= 5:
            buckets["3-5"] += 1
        elif min_yoe <= 8:
            buckets["5-8"] += 1
        else:
            buckets["8+"] += 1
    return buckets


def publications_stats(data: list[dict[str, Any]]) -> dict[str, int]:
    """Count how many roles expect publications vs not."""
    expects = sum(1 for r in data if r.get("publications_expected"))
    return {"expects_publications": expects, "no_publications": len(data) - expects}


ROLE_TYPE_PATTERNS: dict[str, list[str]] = {
    "Research Scientist": ["research scientist", "research sci"],
    "Applied Scientist": ["applied scientist"],
    "Research Engineer": ["research engineer", "research eng"],
    "ML Engineer": [
        "ml engineer", "machine learning engineer", "ml infrastructure",
        "applied ml", "ml sci", "ml platform", "machine learning",
    ],
}


def classify_role_type(title: str) -> str:
    """Classify a role title into one of the four role types."""
    lower = title.lower()
    # Check in priority order (most specific first)
    for role_type, patterns in ROLE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in lower:
                return role_type
    return "Other"


def _compute_group_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute summary stats for a group of roles."""
    total = len(rows)
    if total == 0:
        return {"count": 0}

    # Avg YoE
    yoe_vals = [r["min_yoe"] for r in rows if r.get("min_yoe") is not None]
    avg_yoe = round(sum(yoe_vals) / len(yoe_vals), 1) if yoe_vals else None

    # % PhD
    phd_count = sum(1 for r in rows if r.get("degree_level") == "PhD")
    pct_phd = round(phd_count / total * 100, 1)

    # % publications
    pub_count = sum(1 for r in rows if r.get("publications_expected"))
    pct_pub = round(pub_count / total * 100, 1)

    # Top skills
    skill_counter: Counter[str] = Counter()
    for row in rows:
        raw = row.get("skills")
        if not raw:
            continue
        skills = json.loads(raw) if isinstance(raw, str) else raw
        for skill in set(skills):
            skill_counter[skill] += 1
    top5_skills = [s for s, _ in skill_counter.most_common(5)]

    # Systems skills (CUDA, distributed training, infra, Kubernetes, Docker, C++, Rust)
    systems_keywords = {"cuda", "distributed training", "kubernetes", "docker", "c++",
                        "rust", "infrastructure", "systems", "mlops", "gpu"}
    systems_count = 0
    for row in rows:
        raw = row.get("skills")
        if not raw:
            continue
        skills = json.loads(raw) if isinstance(raw, str) else raw
        langs_raw = row.get("languages")
        langs = json.loads(langs_raw) if isinstance(langs_raw, str) and langs_raw else []
        all_items = {s.lower() for s in skills} | {l.lower() for l in langs}
        if all_items & systems_keywords:
            systems_count += 1
    pct_systems = round(systems_count / total * 100, 1)

    return {
        "count": total,
        "avg_yoe": avg_yoe,
        "pct_phd": pct_phd,
        "pct_publications": pct_pub,
        "pct_systems_skills": pct_systems,
        "top5_skills": top5_skills,
    }


def role_type_comparison(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare requirements across role types (Research Engineer, ML Engineer, etc.)."""
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in data:
        rtype = classify_role_type(row.get("title", ""))
        by_type[rtype].append(row)

    results = []
    for role_type in list(ROLE_TYPE_PATTERNS.keys()) + ["Other"]:
        rows = by_type.get(role_type, [])
        if not rows:
            continue
        stats = _compute_group_stats(rows)
        stats["role_type"] = role_type
        results.append(stats)

    return results


def company_comparison(data: list[dict[str, Any]], top_n: int = 10) -> list[dict[str, Any]]:
    """Cross-company comparison for top N companies by ML/Research role count."""
    # Group rows by company
    by_company: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in data:
        by_company[row["company"]].append(row)

    # Sort companies by role count, take top N
    ranked = sorted(by_company.items(), key=lambda x: len(x[1]), reverse=True)[:top_n]

    results = []
    for company, rows in ranked:
        total = len(rows)

        # Avg YoE (use min_yoe as proxy)
        yoe_vals = [r["min_yoe"] for r in rows if r.get("min_yoe") is not None]
        avg_yoe = round(sum(yoe_vals) / len(yoe_vals), 1) if yoe_vals else None

        # % requiring PhD
        phd_count = sum(1 for r in rows if r.get("degree_level") == "PhD")
        pct_phd = round(phd_count / total * 100, 1)

        # Top 5 skills
        skill_counter: Counter[str] = Counter()
        for row in rows:
            raw = row.get("skills")
            if not raw:
                continue
            skills = json.loads(raw) if isinstance(raw, str) else raw
            for skill in set(skills):
                skill_counter[skill] += 1
        top5_skills = [s for s, _ in skill_counter.most_common(5)]

        # % expecting publications
        pub_count = sum(1 for r in rows if r.get("publications_expected"))
        pct_pub = round(pub_count / total * 100, 1)

        results.append({
            "company": company,
            "role_count": total,
            "avg_yoe": avg_yoe,
            "pct_phd": pct_phd,
            "top5_skills": top5_skills,
            "pct_publications": pct_pub,
        })

    return results


def export_summary(
    comparison: list[dict[str, Any]],
    role_types: list[dict[str, Any]] | None = None,
    output_dir: str = OUTPUT_DIR,
) -> None:
    """Export cross-company and role-type comparison as summary.md and summary.json."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # --- JSON ---
    json_path = Path(output_dir) / "summary.json"
    export_data = {"company_comparison": comparison}
    if role_types:
        export_data["role_type_comparison"] = role_types
    with open(json_path, "w") as f:
        json.dump(export_data, f, indent=2)

    # --- Markdown ---
    md_path = Path(output_dir) / "summary.md"
    lines = [
        "# ML/Research Job Requirements — Summary",
        "",
        "## Cross-Company Comparison",
        "",
        "Top companies by ML/Research role count, with requirements summary.",
        "",
        "| Company | Roles | Avg YoE | % PhD | Top 5 Skills | % Publications |",
        "|---------|-------|---------|-------|--------------|----------------|",
    ]
    for row in comparison:
        avg_yoe_str = str(row["avg_yoe"]) if row["avg_yoe"] is not None else "N/A"
        skills_str = ", ".join(row["top5_skills"]) if row["top5_skills"] else "N/A"
        lines.append(
            f"| {row['company']} | {row['role_count']} | {avg_yoe_str} "
            f"| {row['pct_phd']}% | {skills_str} | {row['pct_publications']}% |"
        )

    if role_types:
        lines.extend([
            "",
            "## Role-Type Comparison",
            "",
            "Requirements breakdown by role type.",
            "",
            "| Role Type | Count | Avg YoE | % PhD | % Publications | % Systems Skills | Top 5 Skills |",
            "|-----------|-------|---------|-------|----------------|------------------|--------------|",
        ])
        for rt in role_types:
            avg_yoe_str = str(rt["avg_yoe"]) if rt.get("avg_yoe") is not None else "N/A"
            skills_str = ", ".join(rt.get("top5_skills", [])) or "N/A"
            lines.append(
                f"| {rt['role_type']} | {rt['count']} | {avg_yoe_str} "
                f"| {rt.get('pct_phd', 0)}% | {rt.get('pct_publications', 0)}% "
                f"| {rt.get('pct_systems_skills', 0)}% | {skills_str} |"
            )

    lines.append("")
    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Exported: {json_path}")
    print(f"Exported: {md_path}")


def run_analysis(db_path: str = DB_PATH) -> dict[str, Any]:
    """Run all analyses and return results dict."""
    conn = get_connection(db_path)
    data = load_requirements(conn)
    conn.close()

    total_roles = len(data)
    roles_with_reqs = sum(1 for r in data if r.get("skills") is not None)

    comparison = company_comparison(data)
    role_types = role_type_comparison(data)
    export_summary(comparison, role_types)

    results = {
        "total_roles": total_roles,
        "roles_with_requirements": roles_with_reqs,
        "top_skills": top_skills(data),
        "degree_distribution": degree_distribution(data),
        "yoe_distribution": yoe_distribution(data),
        "publications": publications_stats(data),
        "company_comparison": comparison,
        "role_type_comparison": role_types,
    }
    return results


def print_report(results: dict[str, Any]) -> None:
    """Print a human-readable analysis report."""
    print(f"\n{'='*60}")
    print(f"  ML/Research Job Requirements Analysis")
    print(f"{'='*60}")
    print(f"\nTotal roles: {results['total_roles']}")
    print(f"Roles with parsed requirements: {results['roles_with_requirements']}")

    print(f"\n--- Top 20 Most-Demanded Skills ---")
    for i, (skill, count) in enumerate(results["top_skills"], 1):
        pct = count / results["total_roles"] * 100 if results["total_roles"] else 0
        print(f"  {i:2d}. {skill:<30s} {count:3d} roles ({pct:.0f}%)")

    print(f"\n--- Degree Requirements Distribution ---")
    for level, count in results["degree_distribution"].items():
        pct = count / results["total_roles"] * 100 if results["total_roles"] else 0
        print(f"  {level:<15s} {count:3d} roles ({pct:.0f}%)")

    print(f"\n--- Years of Experience Distribution ---")
    for bucket, count in results["yoe_distribution"].items():
        pct = count / results["total_roles"] * 100 if results["total_roles"] else 0
        print(f"  {bucket:<15s} {count:3d} roles ({pct:.0f}%)")

    print(f"\n--- Publications Expectations ---")
    pub = results["publications"]
    total = results["total_roles"]
    pct = pub["expects_publications"] / total * 100 if total else 0
    print(f"  Expects publications: {pub['expects_publications']} ({pct:.0f}%)")
    print(f"  No requirement:       {pub['no_publications']}")

    if "role_type_comparison" in results:
        print(f"\n--- Role-Type Comparison ---")
        header = f"  {'Role Type':<25s} {'Count':>5}  {'Avg YoE':>7}  {'%PhD':>5}  {'%Pub':>5}  {'%Sys':>5}  Top Skills"
        print(header)
        print("  " + "-" * 95)
        for rt in results["role_type_comparison"]:
            avg_yoe_str = str(rt["avg_yoe"]) if rt.get("avg_yoe") is not None else "N/A"
            skills_str = ", ".join(rt.get("top5_skills", [])[:3]) or "N/A"
            print(
                f"  {rt['role_type']:<25s} {rt['count']:>5}  {avg_yoe_str:>7}  "
                f"{rt.get('pct_phd', 0):>4.0f}%  {rt.get('pct_publications', 0):>4.0f}%  "
                f"{rt.get('pct_systems_skills', 0):>4.0f}%  {skills_str}"
            )

    if "company_comparison" in results:
        print(f"\n--- Cross-Company Comparison (Top {len(results['company_comparison'])}) ---")
        header = f"  {'Company':<25s} {'Roles':>5}  {'Avg YoE':>7}  {'%PhD':>5}  {'%Pub':>5}  Top Skills"
        print(header)
        print("  " + "-" * 85)
        for row in results["company_comparison"]:
            avg_yoe_str = str(row["avg_yoe"]) if row["avg_yoe"] is not None else "N/A"
            skills_str = ", ".join(row["top5_skills"][:3]) if row["top5_skills"] else "N/A"
            print(
                f"  {row['company']:<25s} {row['role_count']:>5}  {avg_yoe_str:>7}  "
                f"{row['pct_phd']:>4.0f}%  {row['pct_publications']:>4.0f}%  {skills_str}"
            )
    print()


if __name__ == "__main__":
    results = run_analysis()
    print_report(results)
