# Progress Log — AIJobCrawler
Started: 2026-04-09

## Architecture Decisions
(filled by sessions as they make choices)

## Completed Tasks
- **Task 1**: Project setup — created config.py (constants, headers, rate limits, ML_ROLE_KEYWORDS), db.py (SQLite schema with companies/roles/requirements tables + helper functions), requirements.txt, data/ and output/ dirs. Files: config.py, db.py, requirements.txt, data/.gitkeep, output/.gitkeep

- **Task 2**: Built companies.py — 33 AI companies with full metadata (name, url, careers_url, category, founded, hq_location, funding_stage, known_products). Categories: foundation-model (13), ai-infra (7), ai-app (6), ai-chip (5), ai-safety (2). Includes helper functions get_companies_by_category() and get_company_by_name(). Files: companies.py

- **Task 3**: Refactored crawler.py into clean BaseCrawler class. Removed BeautifulSoup demo code and old ProCrawler. New BaseCrawler has: per-domain rate limiting, requests.Session with bot User-Agent from config.py, Bloom filter dedup, retry with backoff, JSONL output, context manager support, subclassable parse() method. Files: crawler.py — 33 AI companies with full metadata (name, url, careers_url, category, founded, hq_location, funding_stage, known_products). Categories: foundation-model (13), ai-infra (7), ai-app (6), ai-chip (5), ai-safety (2). Includes helper functions get_companies_by_category() and get_company_by_name(). Files: companies.py

## Known Issues
(blockers, warnings, things the next session should know)

## Learnings
(gotchas, patterns that worked, things to avoid)
