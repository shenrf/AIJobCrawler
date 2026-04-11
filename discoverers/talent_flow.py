"""Talent flow discoverer — wraps iter2 TalentDiscovery under the common interface.

This is the stealth-catching source: it finds companies via ex-top-lab alumni
on LinkedIn, so it surfaces firms that aren't in any directory (Project
Prometheus, SSI, etc.). Requires a SQLite connection to drive and read
company_discovery, and a GoogleSearchClient to be configured via env vars.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Optional

from .base import CompanyDiscoverer, CompanyRecord


class TalentFlowDiscoverer(CompanyDiscoverer):
    source_name = "talent_flow"

    def __init__(
        self,
        conn: sqlite3.Connection,
        max_queries_per_lab: Optional[int] = None,
        min_talent: int = 2,
    ) -> None:
        self.conn = conn
        self.max_queries_per_lab = max_queries_per_lab
        self.min_talent = min_talent

    def discover(self, limit: Optional[int] = None) -> list[CompanyRecord]:
        from talent_discovery import TalentDiscovery
        from company_aggregator import aggregate_companies

        td = TalentDiscovery(self.conn)
        td.discover_all(max_queries_per_lab=self.max_queries_per_lab)
        aggregate_companies(self.conn, min_talent=self.min_talent)

        rows = self.conn.execute(
            """SELECT company_name, talent_count, talent_sources, category,
                      funding, hq_location, website, description
               FROM company_discovery
               ORDER BY talent_count DESC"""
        ).fetchall()

        records: list[CompanyRecord] = []
        for row in rows:
            if row["talent_count"] < self.min_talent:
                continue
            try:
                sources = json.loads(row["talent_sources"] or "{}")
            except json.JSONDecodeError:
                sources = {}
            records.append(
                CompanyRecord(
                    company_name=row["company_name"],
                    source=self.source_name,
                    website=row["website"] or "",
                    category=row["category"] or "",
                    funding=row["funding"] or "",
                    hq_location=row["hq_location"] or "",
                    description=row["description"] or "",
                    talent_count=row["talent_count"],
                    talent_sources=sources,
                )
            )
            if limit and len(records) >= limit:
                break
        return records
