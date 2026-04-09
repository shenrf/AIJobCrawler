"""Requirements analysis and cross-company comparison for AIJobCrawler."""

import json
import sqlite3
from collections import Counter
from typing import Any

from config import DB_PATH
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


def run_analysis(db_path: str = DB_PATH) -> dict[str, Any]:
    """Run all analyses and return results dict."""
    conn = get_connection(db_path)
    data = load_requirements(conn)
    conn.close()

    total_roles = len(data)
    roles_with_reqs = sum(1 for r in data if r.get("skills") is not None)

    results = {
        "total_roles": total_roles,
        "roles_with_requirements": roles_with_reqs,
        "top_skills": top_skills(data),
        "degree_distribution": degree_distribution(data),
        "yoe_distribution": yoe_distribution(data),
        "publications": publications_stats(data),
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
    print()


if __name__ == "__main__":
    results = run_analysis()
    print_report(results)
