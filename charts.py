"""Chart generation for AIJobCrawler — skill frequency, degree distribution, etc."""

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from pathlib import Path
from typing import Any

from analyze import load_requirements, top_skills
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


def main() -> None:
    """Generate all charts."""
    conn = get_connection()
    data = load_requirements(conn)
    print(f"Loaded {len(data)} roles with requirements.")
    plot_top_skills(data)
    plot_company_skill_heatmap(data)
    conn.close()


if __name__ == "__main__":
    main()
