"""Curated AI company lists discoverer.

Scrapes publicly available "Top AI companies" lists from CB Insights,
Forbes, and other sources. These are editorially curated, high-signal lists
that catch well-funded stealth companies that directories miss.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .base import CompanyDiscoverer, CompanyRecord

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (AIJobCrawler/0.3)"}


def _fetch_ai2_list() -> list[CompanyRecord]:
    """Fetch the AI2 incubator portfolio (Allen Institute for AI spinoffs)."""
    url = "https://allenai.org/incubator"
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.error(f"AI2 incubator page returned {r.status_code}")
            return []
    except requests.RequestException as e:
        logger.error(f"AI2 incubator fetch failed: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    records: list[CompanyRecord] = []
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip()
        href = a["href"]
        if not text or len(text) < 2 or len(text) > 80:
            continue
        if href.startswith(("http://", "https://")) and "allenai.org" not in href:
            if any(skip in href.lower() for skip in ["twitter.", "linkedin.", "github.", "youtube."]):
                continue
            records.append(CompanyRecord(
                company_name=text,
                source="curated_ai2",
                website=href,
                category="ai-app",
                description="AI2 Incubator portfolio company",
            ))
    return records


def _fetch_ml_companies_github_list() -> list[CompanyRecord]:
    """Fetch the awesome-ml-companies GitHub list (community-curated)."""
    urls = [
        "https://raw.githubusercontent.com/krychu/awesome-ai-companies/main/README.md",
        "https://raw.githubusercontent.com/jxnl/awesome-ai-companies/main/README.md",
    ]
    records: list[CompanyRecord] = []
    seen: set[str] = set()

    for url in urls:
        try:
            r = requests.get(url, headers=_HEADERS, timeout=15)
            if r.status_code != 200:
                continue
        except requests.RequestException:
            continue

        for line in r.text.splitlines():
            m = re.match(r"[-*]\s*\[([^\]]+)\]\(([^)]+)\)", line)
            if not m:
                continue
            name, href = m.group(1).strip(), m.group(2).strip()
            if name.lower() in seen or not href.startswith("http"):
                continue
            if any(skip in href for skip in ["github.com", "arxiv.org", "wikipedia.org"]):
                continue
            seen.add(name.lower())
            records.append(CompanyRecord(
                company_name=name,
                source="curated_github",
                website=href,
                category="ai-app",
                description="Community-curated AI company list",
            ))
    return records


def _fetch_otta_top_companies() -> list[CompanyRecord]:
    """Scrape Otta/Welcome to the Jungle top AI companies page."""
    url = "https://app.welcometothejungle.com/organizations?query=artificial+intelligence&aroundQuery=United+States&refinementList%5Bs_organisation_size%5D%5B0%5D=15-50&refinementList%5Bs_organisation_size%5D%5B1%5D=50-250&refinementList%5Bs_organisation_size%5D%5B2%5D=250-1000"
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            return []
    except requests.RequestException:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    records: list[CompanyRecord] = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        name = heading.get_text(strip=True)
        if name and 3 < len(name) < 60:
            parent_a = heading.find_parent("a", href=True)
            link = parent_a["href"] if parent_a else ""
            records.append(CompanyRecord(
                company_name=name,
                source="curated_otta",
                website=link,
                category="ai-app",
                description="Otta/WTTJ top AI company",
            ))
    return records


def _fetch_builtin_ai_companies() -> list[CompanyRecord]:
    """Fetch Builtin.com's AI company list."""
    url = "https://builtin.com/artificial-intelligence/ai-companies-roundup"
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.error(f"Builtin AI list returned {r.status_code}")
            return []
    except requests.RequestException as e:
        logger.error(f"Builtin AI list fetch failed: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    records: list[CompanyRecord] = []
    seen: set[str] = set()

    for heading in soup.find_all(["h2", "h3"]):
        text = heading.get_text(strip=True)
        text = re.sub(r"^\d+[\.\)]\s*", "", text)
        if not text or len(text) > 60 or text.lower() in seen:
            continue
        if any(skip in text.lower() for skip in ["table of contents", "what is", "how to", "why", "faq"]):
            continue
        seen.add(text.lower())
        records.append(CompanyRecord(
            company_name=text,
            source="curated_builtin",
            website="",
            category="ai-app",
            description="Builtin.com top AI company",
        ))
    return records


def _fetch_topai_companies() -> list[CompanyRecord]:
    """Fetch topai.tools or similar aggregator."""
    url = "https://topai.tools/ranking"
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            return []
    except requests.RequestException:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    records: list[CompanyRecord] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip()
        href = a["href"]
        if not text or len(text) < 2 or len(text) > 60 or text.lower() in seen:
            continue
        if href.startswith("http") and "topai.tools" not in href:
            seen.add(text.lower())
            records.append(CompanyRecord(
                company_name=text,
                source="curated_topai",
                website=href,
                category="ai-app",
                description="TopAI.tools ranked AI company/product",
            ))
    return records


class CuratedListsDiscoverer(CompanyDiscoverer):
    source_name = "curated_lists"

    def discover(self, limit: Optional[int] = None) -> list[CompanyRecord]:
        all_records: list[CompanyRecord] = []
        fetchers = [
            ("ai2_incubator", _fetch_ai2_list),
            ("github_awesome", _fetch_ml_companies_github_list),
            ("builtin", _fetch_builtin_ai_companies),
            ("otta", _fetch_otta_top_companies),
            ("topai", _fetch_topai_companies),
        ]
        for name, fn in fetchers:
            try:
                recs = fn()
                logger.info(f"Curated source {name}: {len(recs)} companies")
                all_records.extend(recs)
            except Exception as e:
                logger.error(f"Curated source {name} failed: {e}")

        # Dedupe within this discoverer
        seen: set[str] = set()
        unique: list[CompanyRecord] = []
        for r in all_records:
            key = r.company_name.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(r)
        if limit:
            unique = unique[:limit]
        return unique
