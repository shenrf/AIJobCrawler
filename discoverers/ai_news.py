"""AI funding news discoverer.

Scrapes TechCrunch's AI category RSS and extracts company names from
"X raises $Y" headlines. Captures companies right after funding rounds —
often the most actionable signal for job searching.
"""
from __future__ import annotations

import logging
import re
from typing import Optional
from xml.etree import ElementTree as ET

import requests

from .base import CompanyDiscoverer, CompanyRecord

logger = logging.getLogger(__name__)

_FEED_URL = "https://techcrunch.com/category/artificial-intelligence/feed/"

# Matches "CompanyName raises $100M Series B", "Foo nabs $50 million to", etc.
_FUNDING_RE = re.compile(
    r"^([A-Z][A-Za-z0-9&'\.\-]+(?:\s[A-Z][A-Za-z0-9&'\.\-]+){0,3})"
    r"\s+(?:raises|nabs|lands|secures|snags|closes|bags)"
    r"\s+(?:a\s+)?\$(\d+(?:\.\d+)?)\s?(million|billion|m|b)",
    re.IGNORECASE,
)


class AINewsDiscoverer(CompanyDiscoverer):
    source_name = "ai_news"

    def __init__(self, feed_url: str = _FEED_URL) -> None:
        self.feed_url = feed_url

    def _fetch_feed(self) -> list[dict]:
        try:
            resp = requests.get(
                self.feed_url,
                headers={"User-Agent": "AIJobCrawler/0.2 (bot)"},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.error(f"Feed returned {resp.status_code}")
                return []
            root = ET.fromstring(resp.content)
            items: list[dict] = []
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                description = (item.findtext("description") or "").strip()
                if title:
                    items.append({"title": title, "link": link, "description": description})
            return items
        except (requests.RequestException, ET.ParseError) as e:
            logger.error(f"AI news fetch failed: {e}")
            return []

    def _parse_funding(self, title: str) -> Optional[tuple[str, str]]:
        m = _FUNDING_RE.match(title)
        if not m:
            return None
        name, amount, unit = m.group(1), m.group(2), m.group(3).lower()
        funding = f"${amount}B" if unit in ("b", "billion") else f"${amount}M"
        return name.strip(), funding

    def discover(self, limit: Optional[int] = None) -> list[CompanyRecord]:
        items = self._fetch_feed()
        records: list[CompanyRecord] = []
        seen: set[str] = set()
        for item in items:
            parsed = self._parse_funding(item["title"])
            if not parsed:
                continue
            name, funding = parsed
            if name in seen:
                continue
            seen.add(name)
            records.append(
                CompanyRecord(
                    company_name=name,
                    source=self.source_name,
                    funding=funding,
                    description=item["title"][:500],
                    source_meta={"article": item["link"]},
                )
            )
            if limit and len(records) >= limit:
                break
        return records
