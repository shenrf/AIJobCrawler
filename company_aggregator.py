"""Aggregate talent_moves into company_discovery rows."""
from __future__ import annotations

import json
import sqlite3


def aggregate_companies(conn: sqlite3.Connection, min_talent: int = 2) -> list[dict]:
    """Group talent_moves by (current_company, previous_lab) and write to company_discovery.

    Args:
        conn: SQLite connection (must have talent_moves and company_discovery tables).
        min_talent: Minimum number of talent moves to register a company.

    Returns:
        List of inserted company rows as dicts.
    """
    rows = conn.execute(
        """SELECT current_company, previous_lab, COUNT(*) AS cnt
           FROM talent_moves
           WHERE current_company != ''
           GROUP BY current_company, previous_lab"""
    ).fetchall()

    company_map: dict[str, dict[str, int]] = {}
    for row in rows:
        company = row["current_company"]
        lab = row["previous_lab"]
        cnt = row["cnt"]
        company_map.setdefault(company, {})[lab] = cnt

    inserted: list[dict] = []
    for company, sources in company_map.items():
        total = sum(sources.values())
        if total < min_talent:
            continue
        conn.execute(
            """INSERT INTO company_discovery (company_name, talent_count, talent_sources)
               VALUES (?, ?, ?)
               ON CONFLICT(company_name) DO UPDATE SET
                 talent_count = excluded.talent_count,
                 talent_sources = excluded.talent_sources""",
            (company, total, json.dumps(sources)),
        )
        inserted.append(
            {"company_name": company, "talent_count": total, "talent_sources": sources}
        )
    conn.commit()
    return inserted
