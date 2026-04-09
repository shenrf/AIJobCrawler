"""Chart generation for AIJobCrawler — skill frequency, degree distribution, etc."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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


def main() -> None:
    """Generate all charts."""
    conn = get_connection()
    data = load_requirements(conn)
    print(f"Loaded {len(data)} roles with requirements.")
    plot_top_skills(data)
    conn.close()


if __name__ == "__main__":
    main()
