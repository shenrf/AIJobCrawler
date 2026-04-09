"""End-to-end test for company_crawler.py on 5 companies."""

import json
import logging
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from companies import COMPANIES, get_company_by_name
from company_crawler import CompanyCrawler
from config import DB_PATH
from db import get_connection, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TARGET_COMPANIES = ["Anthropic", "OpenAI", "Mistral AI", "Hugging Face", "Scale AI"]


def main() -> None:
    # Remove existing DB to start fresh
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        logger.info("Removed existing DB at %s", DB_PATH)

    # Filter to our 5 target companies
    targets = [c for c in COMPANIES if c["name"] in TARGET_COMPANIES]
    assert len(targets) == 5, f"Expected 5 companies, found {len(targets)}: {[c['name'] for c in targets]}"

    # Crawl
    logger.info("=== Starting crawl of %d companies ===", len(targets))
    with CompanyCrawler() as crawler:
        results = crawler.crawl_all(targets)

    logger.info("=== Crawl complete: %d results ===", len(results))

    # Verify DB
    conn = get_connection()
    rows = conn.execute("SELECT * FROM companies").fetchall()
    logger.info("=== DB has %d company rows ===", len(rows))

    issues: list[str] = []
    for name in TARGET_COMPANIES:
        row = conn.execute("SELECT * FROM companies WHERE name = ?", (name,)).fetchone()
        if not row:
            issues.append(f"MISSING: {name} not in DB")
            continue

        desc = row["description"] or ""
        tech = row["tech_stack"] or "[]"
        emp = row["employee_count"] or ""
        news = row["recent_news"] or "[]"
        wiki = row["wiki_url"] or ""
        key_people = row["key_people"] or "[]"

        tech_list = json.loads(tech) if tech else []
        news_list = json.loads(news) if news else []
        people_list = json.loads(key_people) if key_people else []

        logger.info(
            "  %s: desc=%d chars, tech=%d, emp='%s', news=%d, wiki=%s, people=%d",
            name, len(desc), len(tech_list), emp, len(news_list),
            "yes" if wiki else "no", len(people_list),
        )

        # Validation checks
        if len(desc) < 50:
            issues.append(f"THIN_DESC: {name} description only {len(desc)} chars")
        if not tech_list and not wiki:
            issues.append(f"NO_TECH: {name} has no tech stack and no wiki fallback")

    conn.close()

    if issues:
        logger.warning("=== %d issues found ===", len(issues))
        for issue in issues:
            logger.warning("  %s", issue)
    else:
        logger.info("=== All checks passed ===")

    # Print summary
    print("\n" + "=" * 60)
    print("E2E TEST SUMMARY")
    print("=" * 60)
    print(f"Companies crawled: {len(results)}/5")
    print(f"Issues: {len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    print("=" * 60)


if __name__ == "__main__":
    main()
