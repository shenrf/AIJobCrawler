# Progress Log — AIJobCrawler
Started: 2026-04-09

## Architecture Decisions
(filled by sessions as they make choices)

## Completed Tasks
- **Task 1**: Project setup — created config.py (constants, headers, rate limits, ML_ROLE_KEYWORDS), db.py (SQLite schema with companies/roles/requirements tables + helper functions), requirements.txt, data/ and output/ dirs. Files: config.py, db.py, requirements.txt, data/.gitkeep, output/.gitkeep

- **Task 2**: Built companies.py — 33 AI companies with full metadata (name, url, careers_url, category, founded, hq_location, funding_stage, known_products). Categories: foundation-model (13), ai-infra (7), ai-app (6), ai-chip (5), ai-safety (2). Includes helper functions get_companies_by_category() and get_company_by_name(). Files: companies.py

- **Task 3**: Refactored crawler.py into clean BaseCrawler class. Removed BeautifulSoup demo code and old ProCrawler. New BaseCrawler has: per-domain rate limiting, requests.Session with bot User-Agent from config.py, Bloom filter dedup, retry with backoff, JSONL output, context manager support, subclassable parse() method. Files: crawler.py — 33 AI companies with full metadata (name, url, careers_url, category, founded, hq_location, funding_stage, known_products). Categories: foundation-model (13), ai-infra (7), ai-app (6), ai-chip (5), ai-safety (2). Includes helper functions get_companies_by_category() and get_company_by_name(). Files: companies.py

- **Task 4**: Built company_crawler.py — CompanyCrawler subclasses BaseCrawler. Crawls each company's homepage + /about fallback. Extracts: description (first 500 chars main text), employee count hints (regex patterns), tech stack mentions (30+ keywords), recent news headlines (CSS selectors for blog/article patterns). Saves to companies table via db.py. Also added description, employee_count, tech_stack, recent_news columns to companies schema and update_company() helper in db.py. Files: company_crawler.py (new), db.py (updated schema + update helper)

- **Task 5**: Added Wikipedia fallback in company_crawler.py. When homepage data is thin (description < 150 chars OR no employee_count), fetches `en.wikipedia.org/wiki/{Company_Name}`. Parses Wikipedia infobox for: founded, HQ, key people, employee count, funding. Falls back to Wikipedia search if direct URL returns non-200. Extracts first paragraph as description. Enriched fields (founded, hq, funding) overwrite static values in DB; key_people and wiki_url stored in new DB columns. Also added `key_people TEXT` and `wiki_url TEXT` columns to companies table schema in db.py. Files: company_crawler.py, db.py

- **Task 6**: E2E tested company_crawler.py on 5 companies (Anthropic, OpenAI, Mistral AI, Hugging Face, Scale AI). Fixed 2 bugs: (1) Wikipedia fallback now triggers when homepage crawl fails entirely (OpenAI returns 403), not just when data is thin; (2) Fixed Wikipedia description extraction — changed `recursive=False` to `recursive=True` on `<p>` search since Wikipedia wraps paragraphs in nested divs. All 5 companies now have descriptions (300-500 chars), employee counts, wiki URLs, and key people in SQLite. Files: company_crawler.py (2 fixes), tests/test_company_crawler_e2e.py (new)

## Known Issues
(blockers, warnings, things the next session should know)

## Learnings
(gotchas, patterns that worked, things to avoid)
