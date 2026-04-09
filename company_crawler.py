"""Company info crawler — extracts description, employee hints, tech stack, and news from company pages."""

import json
import logging
import re
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

from crawler import BaseCrawler
from companies import COMPANIES, Company
from config import DATA_DIR
from db import get_connection, init_db, insert_company, update_company

logger = logging.getLogger(__name__)

# Tech keywords to look for on company pages
TECH_KEYWORDS: list[str] = [
    "PyTorch", "TensorFlow", "JAX", "CUDA", "Triton", "ONNX", "Kubernetes",
    "Docker", "Ray", "Spark", "Kafka", "PostgreSQL", "Redis", "AWS", "GCP",
    "Azure", "Python", "C++", "Rust", "Go", "TypeScript", "React",
    "Transformer", "LLM", "RLHF", "distributed training", "MLOps",
    "fine-tuning", "inference", "embedding", "vector database",
]

# Patterns that hint at employee count
EMPLOYEE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(\d[\d,]*)\+?\s*employees', re.IGNORECASE),
    re.compile(r'team\s+of\s+(\d[\d,]*)', re.IGNORECASE),
    re.compile(r'(\d[\d,]*)\+?\s*(?:people|team members|staff)', re.IGNORECASE),
    re.compile(r'over\s+(\d[\d,]*)\s+(?:employees|people)', re.IGNORECASE),
]


def _extract_main_text(soup: BeautifulSoup) -> str:
    """Extract visible main text from a page, stripped of nav/footer/script."""
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text


def _extract_description(text: str) -> str:
    """Return first 500 chars of meaningful text."""
    return text[:500].strip()


def _extract_employee_count(text: str) -> str | None:
    """Look for employee count hints in text."""
    for pattern in EMPLOYEE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    return None


def _extract_tech_stack(text: str) -> list[str]:
    """Find tech keywords mentioned on the page."""
    text_lower = text.lower()
    found: list[str] = []
    for kw in TECH_KEYWORDS:
        if kw.lower() in text_lower:
            found.append(kw)
    return found


def _extract_news_headlines(soup: BeautifulSoup) -> list[str]:
    """Try to find news/blog headlines from the page."""
    headlines: list[str] = []
    # Look for common blog/news patterns
    for selector in ["article h2", "article h3", ".blog h2", ".news h2",
                     "[class*='post'] h2", "[class*='blog'] h3",
                     "[class*='news'] h3", "h2 a", "h3 a"]:
        for tag in soup.select(selector):
            title = tag.get_text(strip=True)
            if title and 10 < len(title) < 200:
                headlines.append(title)
            if len(headlines) >= 5:
                break
        if headlines:
            break
    return headlines[:5]


WIKIPEDIA_INFOBOX_FIELDS: dict[str, str] = {
    "founded": "founded",
    "headquarters": "hq",
    "key people": "key_people",
    "number of employees": "employee_count",
    "employees": "employee_count",
    "total funding": "funding",
    "funding": "funding",
}


def _wikipedia_search_url(company_name: str) -> str:
    """Return Wikipedia URL for a company name."""
    slug = company_name.replace(" ", "_")
    return f"https://en.wikipedia.org/wiki/{slug}"


def _parse_wikipedia_infobox(soup: BeautifulSoup) -> dict[str, Any]:
    """Parse Wikipedia infobox table for company metadata."""
    result: dict[str, Any] = {}
    infobox = soup.find("table", class_=re.compile(r"infobox"))
    if not infobox or not isinstance(infobox, Tag):
        return result

    for row in infobox.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if not th or not td:
            continue
        label = th.get_text(separator=" ", strip=True).lower()
        value_tag = td
        # Remove citation superscripts
        for sup in value_tag.find_all("sup"):
            sup.decompose()
        value = value_tag.get_text(separator=", ", strip=True)
        # Match label to known fields
        for key, field in WIKIPEDIA_INFOBOX_FIELDS.items():
            if key in label:
                if field == "key_people":
                    # Split on newline/comma
                    people = [p.strip() for p in re.split(r"[\n,]+", value) if p.strip()]
                    result[field] = people[:10]
                else:
                    result[field] = value[:300]
                break

    # Try to get a short description from the first paragraph
    content_div = soup.find("div", class_="mw-parser-output")
    if content_div and isinstance(content_div, Tag):
        for p in content_div.find_all("p", recursive=False):
            text = p.get_text(strip=True)
            if len(text) > 50:
                result["description"] = text[:500]
                break

    return result


def _fetch_wikipedia(session: requests.Session, company_name: str) -> dict[str, Any] | None:
    """Fetch Wikipedia page for a company and parse infobox. Returns None on failure."""
    url = _wikipedia_search_url(company_name)
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            # Try search redirect
            search_url = f"https://en.wikipedia.org/w/index.php?search={requests.utils.quote(company_name)}&ns0=1"
            resp = session.get(search_url, timeout=10)
            if resp.status_code != 200:
                return None
        soup = BeautifulSoup(resp.text, "html.parser")
        # Confirm this is an actual article (not a disambiguation or search results page)
        if soup.find("div", class_="disambigbox") or "search results" in (soup.title.get_text() if soup.title else "").lower():
            return None
        data = _parse_wikipedia_infobox(soup)
        data["wiki_url"] = url
        return data if data else None
    except Exception as exc:
        logger.debug("Wikipedia fetch failed for %s: %s", company_name, exc)
        return None


class CompanyCrawler(BaseCrawler):
    """Crawls company homepages/about pages to extract info."""

    def __init__(self) -> None:
        super().__init__(output_file=f"{DATA_DIR}/companies.jsonl")

    def parse(self, url: str, response: requests.Response) -> list[dict[str, Any]]:
        """Parse a company page and extract description, employee count, tech stack, news."""
        soup = BeautifulSoup(response.text, "html.parser")
        news = _extract_news_headlines(soup)
        text = _extract_main_text(soup)

        record: dict[str, Any] = {
            "url": url,
            "description": _extract_description(text),
            "employee_count": _extract_employee_count(text),
            "tech_stack": _extract_tech_stack(text),
            "recent_news": news,
        }
        return [record]

    def crawl_company(self, company: Company) -> dict[str, Any] | None:
        """Crawl a single company's homepage and optional about page."""
        url = company["url"]
        logger.info("Crawling company: %s (%s)", company["name"], url)

        records = self.crawl_url(url)
        if not records:
            return None

        result = records[0]
        result["name"] = company["name"]

        # Try /about page for richer content if description is thin
        if len(result.get("description", "")) < 100:
            about_url = url.rstrip("/") + "/about"
            about_records = self.crawl_url(about_url)
            if about_records:
                about = about_records[0]
                if len(about.get("description", "")) > len(result.get("description", "")):
                    result["description"] = about["description"]
                result["tech_stack"] = list(set(result.get("tech_stack", []) + about.get("tech_stack", [])))
                if not result.get("employee_count"):
                    result["employee_count"] = about.get("employee_count")
                if not result.get("recent_news") and about.get("recent_news"):
                    result["recent_news"] = about["recent_news"]

        # Wikipedia fallback: if data is still thin, enrich from Wikipedia infobox
        data_is_thin = (
            len(result.get("description", "")) < 150
            or not result.get("employee_count")
        )
        if data_is_thin:
            logger.info("Data thin for %s — trying Wikipedia fallback", company["name"])
            wiki = _fetch_wikipedia(self.session, company["name"])
            if wiki:
                if len(wiki.get("description", "")) > len(result.get("description", "")):
                    result["description"] = wiki["description"]
                if not result.get("employee_count") and wiki.get("employee_count"):
                    result["employee_count"] = wiki["employee_count"]
                if wiki.get("key_people"):
                    result["key_people"] = wiki["key_people"]
                if wiki.get("wiki_url"):
                    result["wiki_url"] = wiki["wiki_url"]
                # Enrich company static fields if better values found
                if wiki.get("founded"):
                    result["founded_wiki"] = wiki["founded"]
                if wiki.get("hq"):
                    result["hq_wiki"] = wiki["hq"]
                if wiki.get("funding"):
                    result["funding_wiki"] = wiki["funding"]
                logger.info("Wikipedia enriched %s: desc=%d, people=%d",
                            company["name"],
                            len(result.get("description", "")),
                            len(result.get("key_people", [])))

        return result

    def crawl_all(self, companies: list[Company] | None = None) -> list[dict[str, Any]]:
        """Crawl all companies and save results to DB."""
        if companies is None:
            companies = COMPANIES

        init_db()
        conn = get_connection()
        results: list[dict[str, Any]] = []

        try:
            for company in companies:
                info = self.crawl_company(company)

                # Insert/get company in DB
                company_id = insert_company(
                    conn,
                    name=company["name"],
                    url=company["url"],
                    careers_url=company["careers_url"],
                    category=company["category"],
                    founded=str(company["founded"]),
                    hq=company["hq_location"],
                    funding=company["funding_stage"],
                    products=", ".join(company["known_products"]),
                )

                # Update with crawled info
                if info:
                    update_fields: dict[str, Any] = {
                        "description": info.get("description"),
                        "employee_count": info.get("employee_count"),
                        "tech_stack": json.dumps(info.get("tech_stack", [])),
                        "recent_news": json.dumps(info.get("recent_news", [])),
                        "key_people": json.dumps(info.get("key_people", [])),
                    }
                    if info.get("wiki_url"):
                        update_fields["wiki_url"] = info["wiki_url"]
                    # Overwrite static fields with Wikipedia-sourced values if present
                    if info.get("founded_wiki"):
                        update_fields["founded"] = info["founded_wiki"]
                    if info.get("hq_wiki"):
                        update_fields["hq"] = info["hq_wiki"]
                    if info.get("funding_wiki"):
                        update_fields["funding"] = info["funding_wiki"]
                    update_company(conn, company_id, **update_fields)
                    results.append(info)
                    logger.info("Saved %s: desc=%d chars, tech=%d, news=%d, people=%d",
                                company["name"],
                                len(info.get("description", "")),
                                len(info.get("tech_stack", [])),
                                len(info.get("recent_news", [])),
                                len(info.get("key_people", [])))
                else:
                    logger.warning("No data crawled for %s", company["name"])
        finally:
            conn.close()

        logger.info("Crawled %d/%d companies successfully", len(results), len(companies))
        return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    with CompanyCrawler() as crawler:
        crawler.crawl_all()
