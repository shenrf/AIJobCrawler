"""Base interface for company discoverers."""
from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompanyRecord:
    """Unified company record emitted by any discoverer.

    Not all fields are populated by every source — discoverers fill what they
    know, and `upsert_company` merges with existing DB rows (never clobbers
    non-empty fields with empty ones).
    """
    company_name: str
    source: str
    website: str = ""
    careers_url: str = ""
    category: str = ""
    funding: str = ""
    hq_location: str = ""
    description: str = ""
    founded: str = ""
    talent_count: int = 0
    talent_sources: dict = field(default_factory=dict)
    source_meta: dict = field(default_factory=dict)


class CompanyDiscoverer(ABC):
    """A pluggable source that emits candidate AI companies."""

    source_name: str = "unknown"

    @abstractmethod
    def discover(self, limit: Optional[int] = None) -> list[CompanyRecord]:
        """Return candidate companies. `limit` caps results where supported."""


def upsert_company(conn: sqlite3.Connection, record: CompanyRecord) -> bool:
    """Merge-insert a discovered company into company_discovery.

    Merge rules:
      - If row doesn't exist: insert with all fields from record.
      - If row exists: for each non-empty field in record, overwrite the DB value.
        For talent_sources (dict): merge keys, summing counts; recompute talent_count.
        `added_to_pipeline` and `enriched` flags are never reset here.

    Returns True if the row was inserted (new), False if merged into existing.
    """
    existing = conn.execute(
        "SELECT * FROM company_discovery WHERE company_name = ?",
        (record.company_name,),
    ).fetchone()

    if existing is None:
        conn.execute(
            """INSERT INTO company_discovery
               (company_name, talent_count, talent_sources, category, funding,
                founded, hq_location, careers_url, website, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.company_name,
                record.talent_count,
                json.dumps(record.talent_sources),
                record.category or "unknown",
                record.funding,
                record.founded,
                record.hq_location,
                record.careers_url,
                record.website,
                record.description,
            ),
        )
        conn.commit()
        return True

    # Merge: keep existing non-empty values unless record has a better one.
    existing_sources = {}
    try:
        existing_sources = json.loads(existing["talent_sources"] or "{}")
    except json.JSONDecodeError:
        existing_sources = {}
    merged_sources = dict(existing_sources)
    for k, v in record.talent_sources.items():
        merged_sources[k] = merged_sources.get(k, 0) + v
    merged_talent_count = sum(merged_sources.values()) if merged_sources else existing["talent_count"]

    conn.execute(
        """UPDATE company_discovery SET
             talent_count = ?,
             talent_sources = ?,
             category = CASE WHEN ? != '' THEN ? ELSE category END,
             funding = CASE WHEN ? != '' THEN ? ELSE funding END,
             founded = CASE WHEN ? != '' THEN ? ELSE founded END,
             hq_location = CASE WHEN ? != '' THEN ? ELSE hq_location END,
             careers_url = CASE WHEN ? != '' THEN ? ELSE careers_url END,
             website = CASE WHEN ? != '' THEN ? ELSE website END,
             description = CASE WHEN ? != '' THEN ? ELSE description END
           WHERE company_name = ?""",
        (
            merged_talent_count,
            json.dumps(merged_sources),
            record.category, record.category,
            record.funding, record.funding,
            record.founded, record.founded,
            record.hq_location, record.hq_location,
            record.careers_url, record.careers_url,
            record.website, record.website,
            record.description, record.description,
            record.company_name,
        ),
    )
    conn.commit()
    return False
