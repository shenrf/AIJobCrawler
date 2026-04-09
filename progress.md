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

- **Task 7**: Built job_crawler.py — JobCrawler subclasses BaseCrawler. Fetches each company's careers_url, extracts job listings from HTML using heuristic link detection (looks for /jobs/, /positions/ URL patterns and role-word text). Filters to ML/Research roles only via `is_ml_role()` using ML_ROLE_KEYWORDS from config.py. Extracts team/location from surrounding HTML context. Saves matching roles to roles table via db.py. Includes `crawl_company()` (single company) and `crawl_all_companies()` (batch) methods. CLI entrypoint prints per-company role counts. Files: job_crawler.py (new), tasks.json (updated)

- **Task 8**: Added Greenhouse, Lever, and Ashby ATS parsers in job_crawler.py. New functions: `fetch_greenhouse_jobs()` (boards-api.greenhouse.io/v1/boards/{slug}/jobs), `fetch_lever_jobs()` (api.lever.co/v0/postings/{slug}?mode=json), `fetch_ashby_jobs()` (api.ashbyhq.com/posting-api/job-board/{slug}). Added `_detect_ats()` which detects ATS platform and slug from careers_url. `crawl_company()` now routes to ATS parsers when detected, falls back to generic HTML parser. Updated companies.py careers_url for: Anthropic → Greenhouse(anthropic), Cohere → Greenhouse(cohere), Scale AI → Greenhouse(scaleai), Character.ai → Greenhouse(characterai), Mistral AI → Lever(mistral), Runway → Lever(runwayml), Together AI → Ashby(together.ai), Perplexity AI → Ashby(perplexity-ai). Files: job_crawler.py, companies.py, tasks.json

- **Task 9**: Built role_parser.py — RoleParser for job detail pages. Extracts: requirements section by matching headings (Requirements, Qualifications, What we're looking for, etc.), YoE via regex (N+ years, N-M years, at least N years), degree level (PhD > MS > BS priority), skills/frameworks (40+ patterns: PyTorch, JAX, CUDA, RLHF, distributed training, etc.), programming languages (Python, C++, Rust, Go, etc.), publication expectations (paper/conference venue mentions). `parse_role_requirements()` fetches a URL and returns parsed dict. `parse_and_save_role()` saves to requirements table. `parse_all_roles()` batch-processes all roles in DB missing requirements. Files: role_parser.py (new), tasks.json (updated)

- **Task 10**: Added WorkDay ATS parser in job_crawler.py. New `fetch_workday_jobs()` uses Workday's undocumented CXS POST API (`/wday/cxs/{tenant}/{board}/jobs`) with pagination. Added Workday detection to `_detect_ats()` — matches `{tenant}.wd{n}.myworkdayjobs.com` URLs and encodes tenant/wd_num/board into a `|`-delimited slug. Wired Workday into `crawl_company()`. Updated companies.py: NVIDIA → `nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite`, AMD → `amd.wd1.myworkdayjobs.com/en-US/External`. Generic HTML fallback (existing `_extract_listings_from_html`) remains the catch-all for any other custom career pages. Files: job_crawler.py, companies.py, tasks.json

- **Task 11**: E2E tested job_crawler.py + role_parser.py on 10 companies across all 4 ATS platforms (Greenhouse, Lever, Ashby, Workday). Results: 10/10 companies crawled without crashes, 81 ML/Research roles found (Anthropic 42, Scale AI 25, Mistral 13, NVIDIA 1), 0 non-ML roles leaked through filter, all FKs valid. Parsed requirements for 8/10 sampled roles (2 failed: 1 Lever timeout, 1 Workday detail page 404). Extraction quality: 88% skills, 88% degree, 75% languages, 50% YoE, 50% publications. Some ATS slugs returned 404 (Cohere, Character.ai, Runway, Together AI, Perplexity AI — likely moved platforms since companies.py was written). Files: tests/test_job_role_e2e.py (new), tasks.json (updated)

## Known Issues
- Cohere, Character.ai Greenhouse slugs return 404 — may have changed ATS platforms
- Runway Lever slug (runwayml) returns 404
- Together AI, Perplexity AI Ashby slugs return 404
- AMD Workday CXS API fails (possible endpoint change)
- NVIDIA Workday detail page URLs return 404 (path format may differ from expected)
(blockers, warnings, things the next session should know)

## Learnings
(gotchas, patterns that worked, things to avoid)
