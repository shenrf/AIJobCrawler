"""Task 11: E2E test of job_crawler.py + role_parser.py on 10 companies across ATS platforms.

Tests:
  - Only ML/Research roles are saved (title filtering)
  - Requirements extracted correctly (skills, degree, YoE, languages, publications)
  - Data in SQLite with correct foreign keys
  - Per-company success/fail logging

Companies (10 total, covering all ATS types):
  Greenhouse: Anthropic, Cohere, Scale AI, Character.ai
  Lever:      Mistral AI, Runway
  Ashby:      Together AI, Perplexity AI
  Workday:    NVIDIA AI, AMD AI
"""

import json
import logging
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from companies import get_company_by_name
from config import ML_ROLE_KEYWORDS
from db import get_connection, init_db
from job_crawler import JobCrawler, is_ml_role
from role_parser import parse_all_roles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("e2e_test")

TEST_DB = "data/test_e2e_task11.db"

TEST_COMPANIES = [
    # Greenhouse
    "Anthropic",
    "Cohere",
    "Scale AI",
    "Character.ai",
    # Lever
    "Mistral AI",
    "Runway",
    # Ashby
    "Together AI",
    "Perplexity AI",
    # Workday
    "NVIDIA AI",
    "AMD AI",
]


def main() -> None:
    start_time = time.time()

    # Clean slate
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)

    companies = []
    for name in TEST_COMPANIES:
        c = get_company_by_name(name)
        if c is None:
            logger.error("Company not found: %s", name)
            continue
        companies.append(c)

    # ── Phase 1: Crawl jobs ──────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PHASE 1: Crawling jobs for %d companies", len(companies))
    logger.info("=" * 60)

    # Monkey-patch DB_PATH so job_crawler uses test DB
    import config
    original_db = config.DB_PATH
    config.DB_PATH = TEST_DB

    results: dict[str, dict] = {}

    with JobCrawler() as crawler:
        conn = get_connection(TEST_DB)
        for company in companies:
            name = company["name"]
            logger.info("--- %s ---", name)
            entry: dict = {"jobs_ok": False, "role_count": 0, "parse_ok": False, "error": None}
            try:
                roles = crawler.crawl_company(company, conn)
                entry["role_count"] = len(roles)
                entry["jobs_ok"] = True
                logger.info("  ✓ %d ML/Research roles found", len(roles))
            except Exception as e:
                entry["error"] = str(e)
                logger.error("  ✗ Job crawl failed: %s", e)
            results[name] = entry
        conn.close()

    # ── Phase 2: Verify ML-only filter ───────────────────────────────────
    logger.info("=" * 60)
    logger.info("PHASE 2: Verifying only ML/Research roles in DB")
    logger.info("=" * 60)

    conn = get_connection(TEST_DB)
    all_roles = conn.execute("SELECT id, title, company_id FROM roles").fetchall()
    non_ml = []
    for role in all_roles:
        if not is_ml_role(role["title"]):
            non_ml.append(role["title"])

    if non_ml:
        logger.warning("  Found %d non-ML roles in DB (filter leak):", len(non_ml))
        for t in non_ml[:10]:
            logger.warning("    - %s", t)
    else:
        logger.info("  ✓ All %d roles in DB match ML/Research keywords", len(all_roles))

    # ── Phase 3: Verify FK integrity ─────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PHASE 3: Checking foreign key integrity")
    logger.info("=" * 60)

    orphan_roles = conn.execute("""
        SELECT r.id, r.title FROM roles r
        LEFT JOIN companies c ON c.id = r.company_id
        WHERE c.id IS NULL
    """).fetchall()
    if orphan_roles:
        logger.error("  ✗ %d roles with broken company FK!", len(orphan_roles))
    else:
        logger.info("  ✓ All roles have valid company_id FK")

    # ── Phase 4: Parse requirements for a sample of roles ────────────────
    logger.info("=" * 60)
    logger.info("PHASE 4: Parsing requirements (up to 3 roles per company)")
    logger.info("=" * 60)

    # Limit to 3 roles per company to keep test fast
    roles_to_parse = conn.execute("""
        SELECT r.id, r.url, r.title, c.name AS company
        FROM roles r
        JOIN companies c ON c.id = r.company_id
        WHERE r.url IS NOT NULL
        GROUP BY c.name, r.id
        ORDER BY c.name, r.id
    """).fetchall()

    # Take up to 3 per company
    from collections import defaultdict
    per_company: dict[str, list] = defaultdict(list)
    for row in roles_to_parse:
        if len(per_company[row["company"]]) < 3:
            per_company[row["company"]].append(row)

    selected = [r for rows in per_company.values() for r in rows]
    logger.info("  Parsing %d roles across %d companies", len(selected), len(per_company))

    conn.close()

    # Use parse_all_roles won't work well with limit per company, so do it manually
    import requests as req_lib
    from role_parser import parse_and_save_role

    sess = req_lib.Session()
    parse_success = 0
    parse_fail = 0

    for row in selected:
        role_id = row["id"]
        url = row["url"]
        company = row["company"]
        title = row["title"]
        logger.info("  [%s] %s", company, title)
        try:
            ok = parse_and_save_role(role_id, url, session=sess, db_path=TEST_DB)
            if ok:
                parse_success += 1
            else:
                parse_fail += 1
                logger.warning("    No content extracted")
        except Exception as e:
            parse_fail += 1
            logger.error("    Parse error: %s", e)

    logger.info("  Requirements parsed: %d success, %d fail", parse_success, parse_fail)

    # ── Phase 5: Verify requirements FK integrity ────────────────────────
    logger.info("=" * 60)
    logger.info("PHASE 5: Verifying requirements data & FK integrity")
    logger.info("=" * 60)

    conn = get_connection(TEST_DB)

    orphan_reqs = conn.execute("""
        SELECT req.id FROM requirements req
        LEFT JOIN roles r ON r.id = req.role_id
        WHERE r.id IS NULL
    """).fetchall()
    if orphan_reqs:
        logger.error("  ✗ %d requirements with broken role FK!", len(orphan_reqs))
    else:
        logger.info("  ✓ All requirements have valid role_id FK")

    # Check that extracted data looks reasonable
    reqs_rows = conn.execute("""
        SELECT req.*, r.title, c.name AS company
        FROM requirements req
        JOIN roles r ON r.id = req.role_id
        JOIN companies c ON c.id = r.company_id
    """).fetchall()

    has_skills = 0
    has_degree = 0
    has_yoe = 0
    has_langs = 0
    has_pubs = 0

    for r in reqs_rows:
        skills = json.loads(r["skills"]) if r["skills"] else []
        langs = json.loads(r["languages"]) if r["languages"] else []
        if skills:
            has_skills += 1
        if r["degree_level"]:
            has_degree += 1
        if r["min_yoe"] is not None:
            has_yoe += 1
        if langs:
            has_langs += 1
        if r["publications_expected"]:
            has_pubs += 1

    total_reqs = len(reqs_rows)
    logger.info("  Requirements summary (%d total):", total_reqs)
    logger.info("    Skills extracted:       %d/%d (%.0f%%)", has_skills, total_reqs, 100 * has_skills / max(total_reqs, 1))
    logger.info("    Degree level found:     %d/%d (%.0f%%)", has_degree, total_reqs, 100 * has_degree / max(total_reqs, 1))
    logger.info("    YoE found:              %d/%d (%.0f%%)", has_yoe, total_reqs, 100 * has_yoe / max(total_reqs, 1))
    logger.info("    Languages found:        %d/%d (%.0f%%)", has_langs, total_reqs, 100 * has_langs / max(total_reqs, 1))
    logger.info("    Publications expected:  %d/%d (%.0f%%)", has_pubs, total_reqs, 100 * has_pubs / max(total_reqs, 1))

    # Print sample extracted requirements
    logger.info("\n  Sample requirements:")
    for r in reqs_rows[:5]:
        skills = json.loads(r["skills"]) if r["skills"] else []
        langs = json.loads(r["languages"]) if r["languages"] else []
        logger.info("    [%s] %s", r["company"], r["title"])
        logger.info("      Degree: %s | YoE: %s-%s | Pubs: %s",
                     r["degree_level"], r["min_yoe"], r["max_yoe"], bool(r["publications_expected"]))
        logger.info("      Skills: %s", ", ".join(skills[:8]) if skills else "none")
        logger.info("      Languages: %s", ", ".join(langs) if langs else "none")

    conn.close()

    # ── Final Summary ────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)
    logger.info("%-25s %8s %8s %s", "Company", "Roles", "ATS", "Status")
    logger.info("-" * 60)

    from job_crawler import _detect_ats
    total_roles = 0
    success_count = 0
    for name in TEST_COMPANIES:
        r = results.get(name, {"jobs_ok": False, "role_count": 0, "error": "not found"})
        c = get_company_by_name(name)
        ats = _detect_ats(c["careers_url"]) if c else None
        ats_label = ats[0] if ats else "html"
        status = "✓" if r["jobs_ok"] else f"✗ {r.get('error', '')[:30]}"
        logger.info("%-25s %8d %8s %s", name, r["role_count"], ats_label, status)
        total_roles += r["role_count"]
        if r["jobs_ok"]:
            success_count += 1

    logger.info("-" * 60)
    logger.info("Total: %d roles from %d/%d companies (%.0fs)",
                total_roles, success_count, len(TEST_COMPANIES), elapsed)
    logger.info("Requirements parsed: %d success, %d fail", parse_success, parse_fail)
    logger.info("Non-ML roles in DB: %d", len(non_ml))

    # Restore
    config.DB_PATH = original_db

    print(f"\nDone. Test DB at {TEST_DB}. Elapsed: {elapsed:.0f}s")
    print(f"Results: {success_count}/{len(TEST_COMPANIES)} companies OK, {total_roles} roles, {parse_success} requirements parsed")


if __name__ == "__main__":
    main()
