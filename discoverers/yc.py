"""Y Combinator directory discoverer.

Queries YC's public Algolia index for companies tagged with AI industries.
Catches well-known and early-stage YC AI startups (Suno, Cognition, Decagon,
Harvey, Cresta, Glean, Perplexity, etc.).
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

from .base import CompanyDiscoverer, CompanyRecord

logger = logging.getLogger(__name__)

# These credentials are embedded in the YC frontend JS and are public.
# If YC rotates them, scrape https://www.ycombinator.com/companies/*.js for new values.
_ALGOLIA_APP_ID = "45BWZJ1SGC"
_ALGOLIA_API_KEY = (
    "NzllNTY5MzJiZGM2OTY2ZTQwMDEzOTNhYWZiZGRjODlhYzVkNjBmOGRjNzJiMWM4ZTU0ZDlh"
    "YTZjOTJiMjlhMWFuYWx5dGljc1RhZ3M9eWNkYyZyZXN0cmljdEluZGljZXM9WUNDb21wYW55"
    "X3Byb2R1Y3Rpb24lMkNZQ0NvbXBhbnlfQnlfTGF1bmNoX0RhdGVfcHJvZHVjdGlvbiZ0YWdG"
    "aWx0ZXJzPSU1QiUyMnljZGNfcHVibGljJTIyJTVE"
)
_ALGOLIA_INDEX = "YCCompany_production"
_ALGOLIA_URL = (
    f"https://{_ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/{_ALGOLIA_INDEX}/query"
)

_AI_TAGS = [
    "Artificial Intelligence",
    "AI",
    "Machine Learning",
    "Generative AI",
    "AIOps",
    "LLMs",
    "Robotics",
    "AI Assistant",
    "AI-Enhanced Learning",
    "Computer Vision",
    "NLP",
    "AI Agents",
]


class YCDiscoverer(CompanyDiscoverer):
    source_name = "yc"

    def __init__(self, tags: Optional[list[str]] = None) -> None:
        self.tags = tags or _AI_TAGS

    def _query(self, hits_per_page: int = 1000) -> list[dict]:
        """POST to Algolia once per tag and return deduped hits by name.

        YC's Algolia index caps results at 1000 regardless of pagination, so
        querying all AI tags in one OR-group (~1885 hits) silently drops ~900
        companies. Instead we issue one request per tag and dedupe client-side.
        """
        headers = {
            "x-algolia-application-id": _ALGOLIA_APP_ID,
            "x-algolia-api-key": _ALGOLIA_API_KEY,
            "content-type": "application/json",
            "User-Agent": "AIJobCrawler/0.2 (bot)",
            "Referer": "https://www.ycombinator.com/",
            "Origin": "https://www.ycombinator.com",
        }
        seen: dict[str, dict] = {}
        for tag in self.tags:
            body = {
                "query": "",
                "facetFilters": [[f"tags:{tag}"]],
                "hitsPerPage": hits_per_page,
            }
            try:
                resp = requests.post(_ALGOLIA_URL, json=body, headers=headers, timeout=15)
                if resp.status_code != 200:
                    logger.error(f"YC Algolia returned {resp.status_code} for tag={tag}")
                    continue
                hits = resp.json().get("hits", [])
            except requests.RequestException as e:
                logger.error(f"YC Algolia request failed for tag={tag}: {e}")
                continue
            for h in hits:
                name = (h.get("name") or "").strip()
                if name and name not in seen:
                    seen[name] = h
        return list(seen.values())

    def discover(self, limit: Optional[int] = None) -> list[CompanyRecord]:
        hits = self._query()
        records: list[CompanyRecord] = []
        for hit in hits:
            name = (hit.get("name") or "").strip()
            if not name:
                continue
            website = (hit.get("website") or "").strip()
            batch = (hit.get("batch") or "").strip()
            one_liner = (hit.get("one_liner") or "").strip()
            long_desc = (hit.get("long_description") or "").strip() or one_liner
            tags = hit.get("tags") or hit.get("industries") or []
            location = (hit.get("all_locations") or "").split(";")[0].strip()

            category = "ai-app"
            tags_l = [t.lower() for t in tags]
            if any("infra" in t or "mlops" in t for t in tags_l):
                category = "ai-infra"
            elif any("robot" in t for t in tags_l):
                category = "robotics"
            elif any("safety" in t or "alignment" in t for t in tags_l):
                category = "ai-safety"

            records.append(
                CompanyRecord(
                    company_name=name,
                    source=self.source_name,
                    website=website,
                    category=category,
                    hq_location=location,
                    description=long_desc[:500],
                    founded=batch,  # e.g. "W21"
                    source_meta={"batch": batch, "tags": tags},
                )
            )
            if limit and len(records) >= limit:
                break
        return records
