"""Run all discoverers, dedupe candidates, upsert into company_discovery."""
from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from .base import CompanyDiscoverer, CompanyRecord, upsert_company

logger = logging.getLogger(__name__)


def _normalize(name: str) -> str:
    """Normalize a company name for dedup: lowercase, stripped, no trailing ' Inc'."""
    n = name.lower().strip()
    for suffix in [" inc.", " inc", " ltd.", " ltd", " llc", " corp.", " corp", ",", "."]:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return n


def run_discoverers(
    conn: sqlite3.Connection,
    discoverers: list[CompanyDiscoverer],
    limit_per_source: Optional[int] = None,
) -> dict:
    """Run each discoverer, merge results, upsert into company_discovery.

    Returns stats: {per_source: {...}, total_candidates, inserted, merged}.
    """
    per_source: dict[str, int] = {}
    all_records: list[CompanyRecord] = []

    for d in discoverers:
        try:
            records = d.discover(limit=limit_per_source)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Discoverer {d.source_name} failed: {e}")
            records = []
        per_source[d.source_name] = len(records)
        all_records.extend(records)

    # Dedupe — keep the first-seen record per normalized name, but merge
    # richer fields (website, funding, etc.) from subsequent records.
    merged_map: dict[str, CompanyRecord] = {}
    for rec in all_records:
        key = _normalize(rec.company_name)
        if key not in merged_map:
            merged_map[key] = rec
            continue
        existing = merged_map[key]
        if not existing.website and rec.website:
            existing.website = rec.website
        if not existing.careers_url and rec.careers_url:
            existing.careers_url = rec.careers_url
        if not existing.funding and rec.funding:
            existing.funding = rec.funding
        if not existing.hq_location and rec.hq_location:
            existing.hq_location = rec.hq_location
        if not existing.founded and rec.founded:
            existing.founded = rec.founded
        if not existing.description and rec.description:
            existing.description = rec.description
        for lab, cnt in rec.talent_sources.items():
            existing.talent_sources[lab] = existing.talent_sources.get(lab, 0) + cnt
        if existing.talent_sources:
            existing.talent_count = sum(existing.talent_sources.values())
        else:
            existing.talent_count = max(existing.talent_count, rec.talent_count)
        # Tag both sources for traceability
        existing.source_meta.setdefault("sources", [existing.source])
        if rec.source not in existing.source_meta["sources"]:
            existing.source_meta["sources"].append(rec.source)

    inserted = merged = 0
    for rec in merged_map.values():
        if upsert_company(conn, rec):
            inserted += 1
        else:
            merged += 1

    return {
        "per_source": per_source,
        "total_candidates": len(all_records),
        "unique_candidates": len(merged_map),
        "inserted": inserted,
        "merged": merged,
    }
