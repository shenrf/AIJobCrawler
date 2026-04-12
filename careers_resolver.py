"""Resolve a careers_url for companies in company_discovery.

For each row with a non-empty `website` and empty `careers_url`:
  1. If website is a huggingface.co profile, fetch HF API to get the real homepage.
  2. Fetch the homepage and look for an <a> tag whose href or text contains
     careers/jobs/join-us.
  3. As a fallback, probe common paths: /careers, /jobs, /join-us.
The resolved URL is written back into company_discovery.careers_url.
"""
from __future__ import annotations

import logging
import re
import sqlite3
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (AIJobCrawler/0.3)"}
_CAREER_HINTS = re.compile(
    r"career|jobs?|join[-_ ]?us|work[-_ ]?with[-_ ]?us|we[-_ ]?are[-_ ]?hiring|openings|positions|hiring",
    re.IGNORECASE,
)
_COMMON_PATHS = ["/careers", "/jobs", "/careers/", "/jobs/", "/join-us", "/company/careers"]

_ATS_HOST_RE = re.compile(
    r"https?://("
    r"boards\.greenhouse\.io/[^/?#\s\"']+"
    r"|jobs\.lever\.co/[^/?#\s\"']+"
    r"|(?:jobs\.)?ashbyhq\.com/[^/?#\s\"']+"
    r"|[^./\s\"']+\.wd\d+\.myworkdayjobs\.com/[^/?#\s\"']*(?:/[^/?#\s\"']+)?"
    r")",
    re.IGNORECASE,
)


def _follow_to_ats(careers_url: str) -> str:
    """If a careers page links to a known ATS (Greenhouse/Lever/Ashby/Workday),
    return the ATS URL so the job crawler can use its structured API.
    Otherwise return the original careers_url unchanged.
    """
    try:
        r = requests.get(careers_url, headers=_HEADERS, timeout=10, allow_redirects=True)
        if r.status_code != 200:
            return careers_url
    except requests.RequestException:
        return careers_url

    # Search the raw HTML first — ATS embeds often live in <script> or <iframe>
    # attrs that BeautifulSoup link extraction would miss.
    m = _ATS_HOST_RE.search(r.text)
    if m:
        return m.group(0)
    return careers_url


def _resolve_hf_org(hf_url: str) -> str:
    """Given a huggingface.co/{org} URL, return the org's homepage (or '')."""
    m = re.match(r"https?://huggingface\.co/([^/?#]+)", hf_url)
    if not m:
        return ""
    org = m.group(1)
    try:
        r = requests.get(
            f"https://huggingface.co/api/organizations/{org}",
            headers=_HEADERS,
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            website = (data.get("url") or data.get("homepage") or "").strip()
            return website
    except requests.RequestException as e:
        logger.debug(f"HF org lookup failed for {org}: {e}")
    return ""


def _find_careers_link(html: str, base_url: str) -> str:
    """Scan HTML for a link that looks like a careers page."""
    soup = BeautifulSoup(html, "html.parser")
    best = ""
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = (a.get_text() or "").strip()
        if _CAREER_HINTS.search(href) or _CAREER_HINTS.search(text):
            full = urljoin(base_url, href)
            # Prefer internal links (same host or no host)
            if urlparse(full).netloc in (urlparse(base_url).netloc, ""):
                return full
            if not best:
                best = full
    return best


def _probe_common_paths(base_url: str) -> str:
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    for path in _COMMON_PATHS:
        url = root + path
        try:
            r = requests.head(url, headers=_HEADERS, timeout=8, allow_redirects=True)
            if r.status_code == 200:
                return r.url
        except requests.RequestException:
            continue
    return ""


def resolve_one(website: str) -> str:
    """Resolve a single company's careers URL from its website."""
    if not website:
        return ""
    if "huggingface.co/" in website:
        website = _resolve_hf_org(website)
        if not website:
            return ""
    try:
        r = requests.get(website, headers=_HEADERS, timeout=10, allow_redirects=True)
        if r.status_code == 200:
            link = _find_careers_link(r.text, r.url)
            if link:
                return _follow_to_ats(link)
    except requests.RequestException as e:
        logger.debug(f"homepage fetch failed for {website}: {e}")
    probed = _probe_common_paths(website)
    return _follow_to_ats(probed) if probed else ""


def upgrade_generic_to_ats(conn: sqlite3.Connection) -> dict[str, int]:
    """Re-scan already-resolved careers URLs and upgrade them to ATS URLs
    (boards.greenhouse.io / jobs.lever.co / *.ashbyhq.com / *.myworkdayjobs.com)
    when the generic page embeds or links to one.
    """
    rows = conn.execute(
        "SELECT id, company_name, careers_url FROM company_discovery "
        "WHERE careers_url != '' AND careers_url != 'SKIP_HF'"
    ).fetchall()

    stats = {"scanned": 0, "upgraded": 0}
    for row in rows:
        current = row["careers_url"]
        if _ATS_HOST_RE.match(current):
            continue  # already ATS
        stats["scanned"] += 1
        upgraded = _follow_to_ats(current)
        if upgraded != current:
            conn.execute(
                "UPDATE company_discovery SET careers_url = ? WHERE id = ?",
                (upgraded, row["id"]),
            )
            conn.commit()
            stats["upgraded"] += 1
    return stats


def resolve_careers_url(
    conn: sqlite3.Connection, limit: int | None = None
) -> dict[str, int]:
    """Resolve careers_url for every row missing one.

    Also updates website when we rewrite a huggingface.co profile to a real
    homepage (so subsequent runs don't re-resolve it).
    """
    sql = (
        "SELECT id, company_name, website FROM company_discovery "
        "WHERE website != '' AND (careers_url IS NULL OR careers_url = '')"
    )
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = conn.execute(sql).fetchall()

    stats = {"scanned": 0, "resolved": 0, "hf_resolved": 0, "failed": 0}
    for row in rows:
        stats["scanned"] += 1
        website = row["website"]
        resolved_site = website
        if "huggingface.co/" in website:
            hf_home = _resolve_hf_org(website)
            if hf_home:
                resolved_site = hf_home
                stats["hf_resolved"] += 1
            else:
                stats["failed"] += 1
                continue
        careers = resolve_one(resolved_site)
        if careers:
            conn.execute(
                "UPDATE company_discovery SET careers_url = ?, website = ? WHERE id = ?",
                (careers, resolved_site, row["id"]),
            )
            conn.commit()
            stats["resolved"] += 1
        else:
            if resolved_site != website:
                conn.execute(
                    "UPDATE company_discovery SET website = ? WHERE id = ?",
                    (resolved_site, row["id"]),
                )
                conn.commit()
            stats["failed"] += 1
    return stats
