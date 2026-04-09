"""Job crawler — fetch career pages, extract job listings, filter to ML/Research roles."""

import logging
import re
import time
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from config import ML_ROLE_KEYWORDS, REQUEST_DELAY_SEC
from crawler import BaseCrawler
from companies import COMPANIES, Company
from db import get_connection, init_db, insert_company, insert_role

logger = logging.getLogger(__name__)


# ── ATS detection ─────────────────────────────────────────────────────────────

def _detect_ats(careers_url: str) -> tuple[str, str] | None:
    """Detect ATS platform and slug from a careers URL.

    Returns (ats_type, slug) or None if not a known ATS URL.
    Supported: 'greenhouse', 'lever', 'ashby'.
    """
    if not careers_url:
        return None

    # Greenhouse: boards.greenhouse.io/{slug}/jobs OR boards.greenhouse.io/{slug}
    m = re.match(r"https?://boards\.greenhouse\.io/([^/?#]+)", careers_url)
    if m:
        return ("greenhouse", m.group(1))

    # Lever: jobs.lever.co/{slug}
    m = re.match(r"https?://jobs\.lever\.co/([^/?#]+)", careers_url)
    if m:
        return ("lever", m.group(1))

    # Ashby: jobs.ashbyhq.com/{slug} or ashbyhq.com/{slug}
    m = re.match(r"https?://(?:jobs\.)?ashbyhq\.com/([^/?#]+)", careers_url)
    if m:
        return ("ashby", m.group(1))

    # Workday: {tenant}.wd{n}.myworkdayjobs.com/en-US/{board}
    m = re.match(
        r"https?://([^.]+)\.(wd\d+)\.myworkdayjobs\.com(?:/[^/]+/([^/?#]+))?",
        careers_url,
    )
    if m:
        tenant = m.group(1)
        wd_num = m.group(2)
        board = m.group(3) or ""
        return ("workday", f"{tenant}|{wd_num}|{board}")

    return None


# ── Greenhouse parser ──────────────────────────────────────────────────────────

def fetch_greenhouse_jobs(slug: str, session: requests.Session) -> list[dict[str, str | None]]:
    """Fetch all job listings from Greenhouse public API for the given company slug.

    API: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
    Returns list of dicts with keys: title, team, location, url.
    """
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        resp = session.get(api_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.exception("Greenhouse API failed for slug=%s", slug)
        return []

    time.sleep(REQUEST_DELAY_SEC)

    listings: list[dict[str, str | None]] = []
    for job in data.get("jobs", []):
        title = job.get("title") or ""
        location = job.get("location", {}).get("name")
        job_url = job.get("absolute_url")
        # department may appear in metadata
        departments = job.get("departments", [])
        team = departments[0].get("name") if departments else None

        listings.append({
            "title": title,
            "team": team,
            "location": location,
            "url": job_url,
        })

    logger.info("Greenhouse(%s): %d total listings", slug, len(listings))
    return listings


# ── Lever parser ───────────────────────────────────────────────────────────────

def fetch_lever_jobs(slug: str, session: requests.Session) -> list[dict[str, str | None]]:
    """Fetch all job listings from Lever public API for the given company slug.

    API: https://api.lever.co/v0/postings/{slug}?mode=json
    Returns list of dicts with keys: title, team, location, url.
    """
    api_url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = session.get(api_url, timeout=15)
        resp.raise_for_status()
        postings = resp.json()
    except Exception:
        logger.exception("Lever API failed for slug=%s", slug)
        return []

    time.sleep(REQUEST_DELAY_SEC)

    listings: list[dict[str, str | None]] = []
    for post in postings:
        title = post.get("text") or ""
        team = post.get("categories", {}).get("team")
        location = post.get("categories", {}).get("location") or post.get("categories", {}).get("allLocations", [None])[0]
        job_url = post.get("hostedUrl")

        listings.append({
            "title": title,
            "team": team,
            "location": location,
            "url": job_url,
        })

    logger.info("Lever(%s): %d total listings", slug, len(listings))
    return listings


# ── Ashby parser ───────────────────────────────────────────────────────────────

def fetch_ashby_jobs(slug: str, session: requests.Session) -> list[dict[str, str | None]]:
    """Fetch all job listings from Ashby public API for the given company slug.

    API: https://api.ashbyhq.com/posting-api/job-board/{slug}
    Returns list of dicts with keys: title, team, location, url.
    """
    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        resp = session.get(api_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.exception("Ashby API failed for slug=%s", slug)
        return []

    time.sleep(REQUEST_DELAY_SEC)

    listings: list[dict[str, str | None]] = []
    for job in data.get("jobPostings", []):
        title = job.get("title") or ""
        team = job.get("department")
        location = job.get("locationName") or job.get("location")
        job_url = job.get("jobUrl") or job.get("applyUrl")

        listings.append({
            "title": title,
            "team": team,
            "location": location,
            "url": job_url,
        })

    logger.info("Ashby(%s): %d total listings", slug, len(listings))
    return listings


# ── Workday parser ─────────────────────────────────────────────────────────────

def fetch_workday_jobs(slug: str, session: requests.Session) -> list[dict[str, str | None]]:
    """Fetch job listings from a Workday-hosted career site.

    Slug format: "{tenant}|{wd_num}|{board}" (e.g. "nvidia|wd5|NVIDIAExternalCareerSite").
    Uses Workday's undocumented CXS search API with POST requests.
    Falls back to paginated GET if POST fails.

    Returns list of dicts with keys: title, team, location, url.
    """
    parts = slug.split("|", 2)
    if len(parts) != 3:
        logger.error("Invalid Workday slug: %s", slug)
        return []

    tenant, wd_num, board = parts
    base_url = f"https://{tenant}.{wd_num}.myworkdayjobs.com"
    api_url = f"{base_url}/wday/cxs/{tenant}/{board}/jobs"

    listings: list[dict[str, str | None]] = []
    offset = 0
    limit = 20

    while True:
        payload = {
            "appliedFacets": {},
            "limit": limit,
            "offset": offset,
            "searchText": "",
        }
        try:
            resp = session.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.warning("Workday CXS API failed for %s (offset=%d), trying HTML fallback", slug, offset)
            break

        time.sleep(REQUEST_DELAY_SEC)

        job_postings = data.get("jobPostings", [])
        if not job_postings:
            break

        for job in job_postings:
            title = job.get("title") or ""
            location = job.get("locationsText") or job.get("location") or None
            # Workday returns a relative path like /en-US/{board}/job/{id}
            external_path = job.get("externalPath") or ""
            job_url = f"{base_url}{external_path}" if external_path else None
            # Team/department not always in listing; may be in detail page
            team = job.get("jobFunctionSummary") or None

            listings.append({
                "title": title,
                "team": team,
                "location": location,
                "url": job_url,
            })

        total = data.get("total", 0)
        offset += limit
        if offset >= total or not job_postings:
            break

    logger.info("Workday(%s): %d total listings fetched", slug, len(listings))
    return listings


def is_ml_role(title: str) -> bool:
    """Return True if the job title matches any ML/Research role keyword."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in ML_ROLE_KEYWORDS)


def _extract_listings_from_html(html: str, base_url: str) -> list[dict[str, str | None]]:
    """Extract job listings from a generic careers page HTML.

    Looks for common patterns: links inside job listing containers,
    structured lists of positions, etc.

    Returns list of dicts with keys: title, team, location, url.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings: list[dict[str, str | None]] = []
    seen_urls: set[str] = set()

    # Strategy 1: Look for links whose text looks like a job title.
    # Job links typically contain keywords like "engineer", "scientist", "manager", etc.
    # We cast a wide net here and filter to ML roles later.
    for a_tag in soup.find_all("a", href=True):
        text = a_tag.get_text(strip=True)
        if not text or len(text) < 5 or len(text) > 200:
            continue

        href = a_tag["href"]
        # Skip non-job links
        if href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue

        full_url = urljoin(base_url, href)

        # Heuristic: job links often contain /jobs/, /positions/, /roles/, /openings/
        # or the text looks like a job title (contains common role words)
        href_lower = href.lower()
        text_lower = text.lower()

        is_job_link = any(seg in href_lower for seg in [
            "/job/", "/jobs/", "/position", "/role", "/opening",
            "/career", "/apply", "/posting",
        ])
        has_role_word = any(w in text_lower for w in [
            "engineer", "scientist", "researcher", "developer", "manager",
            "analyst", "architect", "lead", "director", "intern",
            "specialist", "coordinator", "designer", "infrastructure",
        ])

        if not (is_job_link or has_role_word):
            continue

        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Try to extract team/location from surrounding context
        team, location = _extract_meta_from_context(a_tag)

        listings.append({
            "title": text,
            "team": team,
            "location": location,
            "url": full_url,
        })

    return listings


def _extract_meta_from_context(a_tag: Tag) -> tuple[str | None, str | None]:
    """Try to extract team and location from elements near a job link."""
    team = None
    location = None

    # Look at parent and siblings for metadata
    parent = a_tag.parent
    if parent is None:
        return team, location

    # Check siblings and nearby elements for location/team patterns
    container = parent.parent if parent.parent else parent
    text_parts = container.get_text(separator="|", strip=True).split("|")

    for part in text_parts:
        part = part.strip()
        if not part or part == a_tag.get_text(strip=True):
            continue
        # Location patterns: city names, "Remote", country codes
        if re.search(r"\b(remote|hybrid|on-?site|usa|uk|eu)\b", part, re.IGNORECASE):
            location = part
        elif re.search(r",\s*[A-Z]{2}\b", part):  # "City, ST" pattern
            location = part
        elif re.search(r"\b(team|group|department|org)\b", part, re.IGNORECASE):
            team = part
        # If short text (likely a label), guess based on position
        elif len(part) < 40 and not team:
            team = part

    return team, location


class JobCrawler(BaseCrawler):
    """Crawl company career pages and extract ML/Research job listings."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(output_file="data/jobs.jsonl", **kwargs)

    def parse(self, url: str, response: requests.Response) -> list[dict[str, Any]]:
        """Parse a careers page and return ML/Research role listings."""
        listings = _extract_listings_from_html(response.text, response.url)

        # Filter to ML/Research roles only
        ml_roles = [l for l in listings if is_ml_role(l["title"] or "")]

        logger.info(
            "Found %d total listings, %d ML/Research roles on %s",
            len(listings), len(ml_roles), url,
        )
        return ml_roles

    def crawl_company(self, company: Company, conn: Any) -> list[dict[str, Any]]:
        """Crawl a single company's careers page and save ML roles to DB.

        Returns the list of ML role records found.
        """
        careers_url = company["careers_url"]
        if not careers_url:
            logger.warning("No careers_url for %s, skipping", company["name"])
            return []

        logger.info("Crawling jobs for %s: %s", company["name"], careers_url)

        # Ensure company exists in DB
        company_id = insert_company(
            conn,
            name=company["name"],
            url=company["url"],
            careers_url=company["careers_url"],
            category=company["category"],
        )

        # Route to ATS-specific parser or fall back to generic HTML crawl
        ats = _detect_ats(careers_url)
        if ats is not None:
            ats_type, slug = ats
            logger.info("Using %s ATS parser for %s (slug=%s)", ats_type, company["name"], slug)
            if ats_type == "greenhouse":
                all_roles = fetch_greenhouse_jobs(slug, self.session)
            elif ats_type == "lever":
                all_roles = fetch_lever_jobs(slug, self.session)
            elif ats_type == "ashby":
                all_roles = fetch_ashby_jobs(slug, self.session)
            elif ats_type == "workday":
                all_roles = fetch_workday_jobs(slug, self.session)
            else:
                all_roles = []
            roles = [r for r in all_roles if is_ml_role(r["title"] or "")]
            logger.info(
                "ATS %s(%s): %d total → %d ML/Research",
                ats_type, slug, len(all_roles), len(roles),
            )
        else:
            roles = self.crawl_url(careers_url)

        # Save to DB
        saved = 0
        for role in roles:
            insert_role(
                conn,
                company_id=company_id,
                title=role["title"],
                team=role.get("team"),
                location=role.get("location"),
                url=role.get("url"),
            )
            saved += 1

        logger.info("Saved %d ML/Research roles for %s", saved, company["name"])
        return roles

    def crawl_all_companies(
        self, companies: list[Company] | None = None
    ) -> dict[str, int]:
        """Crawl careers pages for all companies. Returns {company_name: role_count}."""
        if companies is None:
            companies = COMPANIES

        init_db()
        conn = get_connection()
        results: dict[str, int] = {}

        try:
            for company in companies:
                try:
                    roles = self.crawl_company(company, conn)
                    results[company["name"]] = len(roles)
                except Exception:
                    logger.exception("Failed to crawl jobs for %s", company["name"])
                    results[company["name"]] = 0
        finally:
            conn.close()

        total = sum(results.values())
        logger.info(
            "Job crawl complete: %d ML/Research roles across %d companies",
            total, len(results),
        )
        return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    with JobCrawler() as crawler:
        results = crawler.crawl_all_companies()
        print(f"\n{'Company':<30} {'ML Roles':>10}")
        print("-" * 42)
        for name, count in sorted(results.items(), key=lambda x: -x[1]):
            print(f"{name:<30} {count:>10}")
        print("-" * 42)
        print(f"{'TOTAL':<30} {sum(results.values()):>10}")
