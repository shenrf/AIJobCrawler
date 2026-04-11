"""Generate a Markdown tracker of discovered companies ranked by talent signal."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional


def _format_sources(sources_json: str) -> str:
    try:
        sources = json.loads(sources_json or "{}")
    except json.JSONDecodeError:
        return ""
    if not sources:
        return ""
    parts = [f"{lab} ({n})" for lab, n in sorted(sources.items(), key=lambda x: -x[1])]
    return ", ".join(parts)


def generate_tracker_md(
    conn: sqlite3.Connection, output_path: Optional[str | Path] = None
) -> str:
    """Build markdown ranking companies by talent inflow. Optionally write to path."""
    rows = conn.execute(
        """SELECT company_name, talent_count, talent_sources, category, funding,
                  hq_location, website, description
           FROM company_discovery
           ORDER BY talent_count DESC, company_name ASC"""
    ).fetchall()

    lines: list[str] = []
    lines.append("# AI Talent Flow Tracker")
    lines.append("")
    lines.append("Companies ranked by ex-top-lab talent inflow.")
    lines.append("")
    lines.append("| Rank | Company | Talent Inflow | Sources | Category | Funding | HQ |")
    lines.append("|------|---------|---------------|---------|----------|---------|----|")

    stealth: list[sqlite3.Row] = []
    rank = 0
    for row in rows:
        has_website = bool(row["website"])
        has_funding = bool(row["funding"])
        if not has_website and not has_funding:
            stealth.append(row)
            continue
        rank += 1
        name_cell = f"[{row['company_name']}]({row['website']})" if has_website else row["company_name"]
        lines.append(
            f"| {rank} | {name_cell} | {row['talent_count']} | "
            f"{_format_sources(row['talent_sources'])} | "
            f"{row['category'] or ''} | {row['funding'] or ''} | {row['hq_location'] or ''} |"
        )

    if stealth:
        lines.append("")
        lines.append("## Stealth / Unverified")
        lines.append("")
        lines.append("Companies with no website and no known funding — possible stealth mode.")
        lines.append("")
        lines.append("| Company | Talent Inflow | Sources |")
        lines.append("|---------|---------------|---------|")
        for row in stealth:
            lines.append(
                f"| {row['company_name']} | {row['talent_count']} | "
                f"{_format_sources(row['talent_sources'])} |"
            )

    md = "\n".join(lines) + "\n"
    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md, encoding="utf-8")
    return md
