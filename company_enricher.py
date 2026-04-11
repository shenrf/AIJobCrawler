"""Enrich discovered companies with category, funding, HQ, website via Google search."""
from __future__ import annotations

import logging
import re
import sqlite3
from typing import Optional

from search_client import GoogleSearchClient

logger = logging.getLogger(__name__)


_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "foundation-model": ["foundation model", "large language model", "llm", "frontier model"],
    "robotics": ["robot", "robotic", "humanoid", "manipulation", "embodied"],
    "ai-infra": ["infrastructure", "gpu cloud", "inference", "training platform", "ai infra"],
    "ai-app": ["productivity", "consumer app", "assistant", "workflow"],
    "ai-agent": ["agent", "autonomous", "browser agent", "coding agent"],
    "ai-safety": ["alignment", "safety", "interpretability", "evals"],
    "ai-chip": ["chip", "silicon", "asic", "accelerator", "tpu"],
}

_FUNDING_RE = re.compile(
    r"\$\s?(\d+(?:\.\d+)?)\s?(million|billion|m|b)\b", re.IGNORECASE
)

_KNOWN_CITIES: list[str] = [
    "San Francisco", "Palo Alto", "Mountain View", "Menlo Park", "Redwood City",
    "New York", "Brooklyn", "Boston", "Cambridge", "Seattle", "Bellevue",
    "Austin", "Los Angeles", "San Diego", "Chicago", "Denver", "Toronto",
    "London", "Paris", "Berlin", "Zurich", "Tel Aviv", "Singapore", "Tokyo",
    "Beijing", "Shanghai", "Hangzhou", "Shenzhen", "Hong Kong", "Bangalore",
]


def _classify_category(text: str) -> str:
    text_l = text.lower()
    best: Optional[str] = None
    best_count = 0
    for cat, kws in _CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in kws if kw in text_l)
        if count > best_count:
            best_count = count
            best = cat
    return best or "unknown"


def _extract_funding(text: str) -> str:
    m = _FUNDING_RE.search(text)
    if not m:
        return ""
    amount, unit = m.group(1), m.group(2).lower()
    if unit in ("b", "billion"):
        return f"${amount}B"
    return f"${amount}M"


def _extract_hq(text: str) -> str:
    for city in _KNOWN_CITIES:
        if city in text:
            return city
    return ""


def _extract_website(results: list[dict], company: str) -> str:
    """Pick the most likely homepage URL from results."""
    company_slug = re.sub(r"[^a-z0-9]", "", company.lower())
    for r in results:
        url = r.get("url", "")
        if not url or "linkedin.com" in url:
            continue
        # Rough match: company slug appears in domain
        domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        if company_slug and company_slug[:6] in domain.replace(".", "").lower():
            return f"https://{domain}"
    return ""


def enrich_company(
    conn: sqlite3.Connection,
    company_name: str,
    client: Optional[GoogleSearchClient] = None,
) -> dict:
    """Enrich one company row by searching Google and parsing results."""
    client = client or GoogleSearchClient()
    query = f"{company_name} AI startup funding"
    results = client.search(query)

    combined = " ".join(
        [f"{r.get('title','')} {r.get('snippet','')}" for r in results]
    )
    description = results[0]["snippet"] if results else ""
    website = _extract_website(results, company_name)
    category = _classify_category(combined)
    funding = _extract_funding(combined)
    hq = _extract_hq(combined)

    conn.execute(
        """UPDATE company_discovery
           SET category = ?, funding = ?, hq_location = ?, website = ?,
               description = ?, enriched = 1
           WHERE company_name = ?""",
        (category, funding, hq, website, description, company_name),
    )
    conn.commit()

    return {
        "company_name": company_name,
        "category": category,
        "funding": funding,
        "hq_location": hq,
        "website": website,
        "description": description,
    }


def enrich_all_companies(
    conn: sqlite3.Connection,
    client: Optional[GoogleSearchClient] = None,
) -> int:
    """Enrich all company_discovery rows where enriched=0. Returns count processed."""
    client = client or GoogleSearchClient()
    rows = conn.execute(
        "SELECT company_name FROM company_discovery WHERE enriched = 0"
    ).fetchall()
    count = 0
    for row in rows:
        try:
            enrich_company(conn, row["company_name"], client=client)
            count += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to enrich {row['company_name']}: {e}")
    return count
