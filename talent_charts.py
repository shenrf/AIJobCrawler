"""Charts for talent flow: Sankey, ranking bar, lab×company heatmap."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def _talent_rows(conn: sqlite3.Connection, top_n: int = 20) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT company_name, talent_count, talent_sources
           FROM company_discovery
           ORDER BY talent_count DESC
           LIMIT ?""",
        (top_n,),
    ).fetchall()


def generate_sankey(
    conn: sqlite3.Connection,
    output_path: str | Path,
    top_n: int = 20,
) -> Path:
    """Plotly Sankey: source labs → destination companies. Saves HTML."""
    import plotly.graph_objects as go  # type: ignore

    rows = _talent_rows(conn, top_n)
    labs: list[str] = []
    companies: list[str] = []
    flows: list[tuple[str, str, int]] = []
    for row in rows:
        company = row["company_name"]
        if company not in companies:
            companies.append(company)
        sources = json.loads(row["talent_sources"] or "{}")
        for lab, cnt in sources.items():
            if lab not in labs:
                labs.append(lab)
            flows.append((lab, company, cnt))

    nodes = labs + companies
    node_index = {n: i for i, n in enumerate(nodes)}
    source = [node_index[l] for l, _, _ in flows]
    target = [node_index[c] for _, c, _ in flows]
    value = [v for _, _, v in flows]

    fig = go.Figure(
        go.Sankey(
            node=dict(label=nodes, pad=15, thickness=20),
            link=dict(source=source, target=target, value=value),
        )
    )
    fig.update_layout(title_text="AI Talent Flow: Source Labs → Destination Companies", font_size=12)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out))
    return out


def generate_company_ranking_bar(
    conn: sqlite3.Connection,
    output_path: str | Path,
    top_n: int = 20,
) -> Path:
    """Matplotlib horizontal bar chart of top companies by talent count."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore

    rows = _talent_rows(conn, top_n)
    names = [r["company_name"] for r in rows][::-1]
    counts = [r["talent_count"] for r in rows][::-1]

    fig, ax = plt.subplots(figsize=(10, max(4, 0.35 * len(names))))
    ax.barh(names, counts, color="steelblue")
    ax.set_xlabel("Talent Inflow (ex-top-lab alumni)")
    ax.set_title(f"Top {len(names)} AI Companies by Talent Signal")
    for i, v in enumerate(counts):
        ax.text(v, i, f" {v}", va="center")
    plt.tight_layout()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out), dpi=150)
    plt.close(fig)
    return out


def generate_talent_heatmap(
    conn: sqlite3.Connection,
    output_path: str | Path,
    top_n: int = 15,
) -> Path:
    """Matplotlib heatmap of source lab × destination company with counts."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore
    import numpy as np

    rows = _talent_rows(conn, top_n)
    companies: list[str] = [r["company_name"] for r in rows]
    labs: list[str] = []
    for r in rows:
        for lab in json.loads(r["talent_sources"] or "{}").keys():
            if lab not in labs:
                labs.append(lab)

    matrix = np.zeros((len(labs), len(companies)), dtype=int)
    for j, r in enumerate(rows):
        sources = json.loads(r["talent_sources"] or "{}")
        for lab, cnt in sources.items():
            i = labs.index(lab)
            matrix[i, j] = cnt

    fig, ax = plt.subplots(figsize=(max(8, 0.6 * len(companies)), max(4, 0.4 * len(labs))))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(companies)))
    ax.set_xticklabels(companies, rotation=45, ha="right")
    ax.set_yticks(range(len(labs)))
    ax.set_yticklabels(labs)
    for i in range(len(labs)):
        for j in range(len(companies)):
            if matrix[i, j] > 0:
                ax.text(j, i, str(matrix[i, j]), ha="center", va="center", color="black", fontsize=8)
    fig.colorbar(im, ax=ax, label="Talent count")
    ax.set_title("Talent Flow: Source Lab × Destination Company")
    plt.tight_layout()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out), dpi=150)
    plt.close(fig)
    return out
