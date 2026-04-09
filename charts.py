"""Chart generation for AIJobCrawler — skill frequency, degree distribution, etc."""

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from pathlib import Path
from typing import Any

from analyze import load_requirements, top_skills, degree_distribution, classify_role_type
from config import DB_PATH, OUTPUT_DIR
from db import get_connection


def plot_top_skills(data: list[dict[str, Any]], n: int = 20, output_path: Path | None = None) -> Path:
    """Horizontal bar chart of top N most-demanded skills. Returns path to saved PNG."""
    if output_path is None:
        output_path = Path(OUTPUT_DIR) / "top_skills.png"

    skills = top_skills(data, n=n)
    if not skills:
        print("No skills data to plot.")
        return output_path

    # Reverse so highest is at top
    labels = [s[0] for s in reversed(skills)]
    counts = [s[1] for s in reversed(skills)]

    fig, ax = plt.subplots(figsize=(10, max(6, len(labels) * 0.4)))
    bars = ax.barh(labels, counts, color="#4C72B0", edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Number of Roles", fontsize=12)
    ax.set_title(f"Top {len(labels)} Most-Demanded Skills for ML/Research Roles", fontsize=14, fontweight="bold")
    ax.tick_params(axis="y", labelsize=10)

    # Add count labels on bars
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(count), va="center", fontsize=9)

    ax.set_xlim(0, max(counts) * 1.15 if counts else 1)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


def plot_company_skill_heatmap(
    data: list[dict[str, Any]],
    n_companies: int = 15,
    n_skills: int = 15,
    output_path: Path | None = None,
) -> Path:
    """Heatmap: top N companies (rows) vs top N skills (columns).

    Cell value = % of that company's roles requiring the skill.
    Saved as output/company_skill_heatmap.png.
    """
    if output_path is None:
        output_path = Path(OUTPUT_DIR) / "company_skill_heatmap.png"

    # Determine top N skills globally
    global_top = top_skills(data, n=n_skills)
    if not global_top:
        print("No skills data to plot heatmap.")
        return output_path
    top_skill_names = [s[0] for s in global_top]

    # Count roles per company
    company_roles: dict[str, list[dict]] = defaultdict(list)
    for row in data:
        company_roles[row["company"]].append(row)

    # Select top N companies by role count
    sorted_companies = sorted(company_roles.items(), key=lambda kv: len(kv[1]), reverse=True)
    top_companies = sorted_companies[:n_companies]

    if not top_companies:
        print("No company data to plot heatmap.")
        return output_path

    # Build matrix: rows = companies, cols = skills
    matrix = np.zeros((len(top_companies), len(top_skill_names)), dtype=float)
    company_labels = []
    for i, (company, roles) in enumerate(top_companies):
        company_labels.append(f"{company} ({len(roles)})")
        for j, skill in enumerate(top_skill_names):
            roles_with_skill = sum(
                1 for r in roles
                if r.get("skills") and skill in (
                    json.loads(r["skills"]) if isinstance(r["skills"], str) else r["skills"]
                )
            )
            matrix[i, j] = roles_with_skill / len(roles) * 100

    # Plot
    fig_w = max(12, n_skills * 0.9)
    fig_h = max(6, n_companies * 0.55)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", vmin=0, vmax=100)

    ax.set_xticks(range(len(top_skill_names)))
    ax.set_xticklabels(top_skill_names, rotation=40, ha="right", fontsize=9)
    ax.set_yticks(range(len(company_labels)))
    ax.set_yticklabels(company_labels, fontsize=9)

    # Annotate cells
    for i in range(len(company_labels)):
        for j in range(len(top_skill_names)):
            val = matrix[i, j]
            text_color = "white" if val > 60 else "black"
            ax.text(j, i, f"{val:.0f}%", ha="center", va="center",
                    fontsize=7, color=text_color)

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("% of roles requiring skill", fontsize=10)

    ax.set_title(
        f"Top {len(top_companies)} Companies × Top {len(top_skill_names)} Skills\n"
        "Cell = % of company's ML/Research roles requiring the skill",
        fontsize=12, fontweight="bold", pad=12,
    )

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


def plot_degree_requirements(data: list[dict[str, Any]], output_path: Path | None = None) -> Path:
    """Donut chart of overall degree distribution + grouped bar by role type.

    Saves both subplots in a single figure to output/degree_requirements.png.
    """
    if output_path is None:
        output_path = Path(OUTPUT_DIR) / "degree_requirements.png"

    DEGREE_ORDER = ["PhD", "MS", "BS", "Not Specified"]
    DEGREE_COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]

    # ── Overall distribution ──────────────────────────────────────────────────
    dist = degree_distribution(data)
    labels_overall = [d for d in DEGREE_ORDER if dist.get(d, 0) > 0]
    sizes_overall = [dist[d] for d in labels_overall]
    colors_overall = [DEGREE_COLORS[DEGREE_ORDER.index(d)] for d in labels_overall]

    # ── Per role-type distribution ────────────────────────────────────────────
    ROLE_TYPES = ["Research Scientist", "Applied Scientist", "Research Engineer", "ML Engineer", "Other"]
    from collections import defaultdict as _dd
    by_type: dict[str, list[dict]] = _dd(list)
    for row in data:
        by_type[classify_role_type(row.get("title", ""))].append(row)

    active_roles = [rt for rt in ROLE_TYPES if by_type.get(rt)]
    # Matrix: rows = degree, cols = role type  (percentage per role type)
    grouped: dict[str, list[float]] = {d: [] for d in DEGREE_ORDER}
    for rt in active_roles:
        rt_dist = degree_distribution(by_type[rt])
        total = len(by_type[rt]) or 1
        for d in DEGREE_ORDER:
            grouped[d].append(rt_dist.get(d, 0) / total * 100)

    # ── Figure ────────────────────────────────────────────────────────────────
    fig, (ax_donut, ax_bar) = plt.subplots(1, 2, figsize=(16, 6))

    # Donut
    wedges, texts, autotexts = ax_donut.pie(
        sizes_overall,
        labels=labels_overall,
        colors=colors_overall,
        autopct="%1.1f%%",
        startangle=140,
        wedgeprops={"width": 0.55, "edgecolor": "white", "linewidth": 1.5},
        pctdistance=0.78,
    )
    for t in autotexts:
        t.set_fontsize(10)
    ax_donut.set_title(
        "Degree Requirements — Overall\n(All ML/Research Roles)",
        fontsize=13, fontweight="bold",
    )

    # Grouped bar
    x = np.arange(len(active_roles))
    bar_width = 0.18
    for idx, (degree, color) in enumerate(zip(DEGREE_ORDER, DEGREE_COLORS)):
        if not any(grouped[degree]):
            continue
        offsets = x + (idx - 1.5) * bar_width
        bars = ax_bar.bar(offsets, grouped[degree], bar_width,
                          label=degree, color=color, edgecolor="white", linewidth=0.5)
        for bar in bars:
            h = bar.get_height()
            if h > 2:
                ax_bar.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                            f"{h:.0f}%", ha="center", va="bottom", fontsize=7.5)

    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(active_roles, fontsize=10, rotation=15, ha="right")
    ax_bar.set_ylabel("% of Roles", fontsize=11)
    ax_bar.set_ylim(0, 105)
    ax_bar.set_title(
        "Degree Requirements by Role Type",
        fontsize=13, fontweight="bold",
    )
    ax_bar.legend(title="Degree", fontsize=9, title_fontsize=10, loc="upper right")
    ax_bar.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax_bar.set_axisbelow(True)

    fig.tight_layout(pad=3.0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


def plot_experience_requirements(
    data: list[dict[str, Any]],
    n_companies: int = 10,
    output_path: Path | None = None,
) -> Path:
    """YoE histogram (overall) + box plot of YoE ranges by top N companies.

    Saved as output/experience_requirements.png.
    """
    if output_path is None:
        output_path = Path(OUTPUT_DIR) / "experience_requirements.png"

    # Collect min_yoe values
    all_yoe: list[float] = [
        float(r["min_yoe"]) for r in data if r.get("min_yoe") is not None
    ]

    # Group by company
    from collections import defaultdict as _dd
    company_yoe: dict[str, list[float]] = _dd(list)
    for r in data:
        if r.get("min_yoe") is not None:
            company_yoe[r["company"]].append(float(r["min_yoe"]))

    # Top N companies by number of YoE data points
    top_companies = sorted(company_yoe.items(), key=lambda kv: len(kv[1]), reverse=True)[:n_companies]

    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(16, 6))

    # ── Histogram ─────────────────────────────────────────────────────────────
    if all_yoe:
        max_yoe = int(max(all_yoe))
        bins = list(range(0, max_yoe + 3))
        ax_hist.hist(all_yoe, bins=bins, color="#4C72B0", edgecolor="white", linewidth=0.8, align="left")
        ax_hist.set_xlabel("Minimum Years of Experience", fontsize=12)
        ax_hist.set_ylabel("Number of Roles", fontsize=12)
        ax_hist.set_title(
            "YoE Distribution — All ML/Research Roles",
            fontsize=13, fontweight="bold",
        )
        ax_hist.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax_hist.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax_hist.set_axisbelow(True)
        # Annotate median
        median_val = float(np.median(all_yoe))
        ax_hist.axvline(median_val, color="#C44E52", linewidth=1.8, linestyle="--", label=f"Median: {median_val:.1f} yrs")
        ax_hist.legend(fontsize=10)
    else:
        ax_hist.text(0.5, 0.5, "No YoE data available", ha="center", va="center",
                     fontsize=12, transform=ax_hist.transAxes)
        ax_hist.set_title("YoE Distribution — All ML/Research Roles", fontsize=13, fontweight="bold")

    # ── Box plot ──────────────────────────────────────────────────────────────
    if top_companies:
        box_data = [yoe_list for _, yoe_list in top_companies]
        box_labels = [
            f"{name}\n(n={len(yoe_list)})"
            for name, yoe_list in top_companies
        ]
        bp = ax_box.boxplot(
            box_data,
            vert=True,
            patch_artist=True,
            medianprops={"color": "#C44E52", "linewidth": 2},
        )
        colors = plt.cm.tab10.colors  # type: ignore[attr-defined]
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax_box.set_xticks(range(1, len(box_labels) + 1))
        ax_box.set_xticklabels(box_labels, fontsize=8.5, rotation=20, ha="right")
        ax_box.set_ylabel("Minimum Years of Experience", fontsize=12)
        ax_box.set_title(
            f"YoE Ranges by Company (Top {len(top_companies)} by data points)",
            fontsize=13, fontweight="bold",
        )
        ax_box.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax_box.set_axisbelow(True)
    else:
        ax_box.text(0.5, 0.5, "No per-company YoE data available", ha="center", va="center",
                    fontsize=12, transform=ax_box.transAxes)
        ax_box.set_title(
            f"YoE Ranges by Company (Top {n_companies})",
            fontsize=13, fontweight="bold",
        )

    fig.tight_layout(pad=3.0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


def plot_role_landscape_sunburst(
    data: list[dict[str, Any]],
    top_n_skills: int = 5,
    output_path: Path | None = None,
) -> Path:
    """Interactive sunburst: category > company > role type > top skills.

    Saves as output/role_landscape.html.
    """
    import plotly.graph_objects as go

    if output_path is None:
        output_path = Path(OUTPUT_DIR) / "role_landscape.html"

    ids: list[str] = []
    labels: list[str] = []
    parents: list[str] = []
    values: list[int] = []

    # Group data: category -> company -> role_type -> skills
    from collections import Counter

    cat_comp: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in data:
        cat = row.get("category") or "Unknown"
        company = row.get("company") or "Unknown"
        cat_comp[cat][company].append(row)

    # Root level: categories
    for cat, companies in sorted(cat_comp.items()):
        cat_total = sum(len(roles) for roles in companies.values())
        cat_id = cat
        ids.append(cat_id)
        labels.append(cat)
        parents.append("")
        values.append(cat_total)

        for company, roles in sorted(companies.items(), key=lambda kv: -len(kv[1])):
            comp_id = f"{cat}/{company}"
            ids.append(comp_id)
            labels.append(company)
            parents.append(cat_id)
            values.append(len(roles))

            # Group by role type
            rt_groups: dict[str, list[dict]] = defaultdict(list)
            for r in roles:
                rt = classify_role_type(r.get("title", ""))
                rt_groups[rt].append(r)

            for rt, rt_roles in sorted(rt_groups.items(), key=lambda kv: -len(kv[1])):
                rt_id = f"{cat}/{company}/{rt}"
                ids.append(rt_id)
                labels.append(rt)
                parents.append(comp_id)
                values.append(len(rt_roles))

                # Top skills for this group
                skill_counter: Counter[str] = Counter()
                for r in rt_roles:
                    skills_raw = r.get("skills")
                    if skills_raw:
                        sk = json.loads(skills_raw) if isinstance(skills_raw, str) else skills_raw
                        for s in sk:
                            skill_counter[s] += 1

                for skill, count in skill_counter.most_common(top_n_skills):
                    skill_id = f"{cat}/{company}/{rt}/{skill}"
                    ids.append(skill_id)
                    labels.append(skill)
                    parents.append(rt_id)
                    values.append(count)

    if not ids:
        print("No data for sunburst.")
        return output_path

    fig = go.Figure(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        maxdepth=3,
        insidetextorientation="radial",
    ))

    fig.update_layout(
        title="ML/Research Role Landscape<br><sub>Category → Company → Role Type → Top Skills</sub>",
        width=900,
        height=900,
        margin=dict(t=80, l=10, r=10, b=10),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path))
    print(f"Saved: {output_path}")
    return output_path


def plot_roles_by_company(
    data: list[dict[str, Any]],
    output_path: Path | None = None,
) -> Path:
    """Bar chart of ML/Research role count by company. Saved as output/roles_by_company.png."""
    if output_path is None:
        output_path = Path(OUTPUT_DIR) / "roles_by_company.png"

    company_counts: dict[str, int] = defaultdict(int)
    for row in data:
        company_counts[row.get("company", "Unknown")] += 1

    if not company_counts:
        print("No data for roles by company chart.")
        return output_path

    sorted_companies = sorted(company_counts.items(), key=lambda kv: kv[1], reverse=True)
    names = [c[0] for c in sorted_companies]
    counts = [c[1] for c in sorted_companies]

    fig, ax = plt.subplots(figsize=(max(10, len(names) * 0.5), 6))
    bars = ax.bar(range(len(names)), counts, color="#4C72B0", edgecolor="white", linewidth=0.5)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(count), ha="center", va="bottom", fontsize=9)

    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Number of ML/Research Roles", fontsize=12)
    ax.set_title("ML/Research Role Count by Company", fontsize=14, fontweight="bold")
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(counts) * 1.15 if counts else 1)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    return output_path


def main() -> None:
    """Generate all charts."""
    conn = get_connection()
    data = load_requirements(conn)
    print(f"Loaded {len(data)} roles with requirements.")
    plot_top_skills(data)
    plot_company_skill_heatmap(data)
    plot_degree_requirements(data)
    plot_experience_requirements(data)
    plot_role_landscape_sunburst(data)
    plot_roles_by_company(data)
    conn.close()


if __name__ == "__main__":
    main()
