# AIJobCrawler

## Project Overview
Web crawler that scans promising AI companies, collects their open job roles and company information, then produces structured summaries and charts.

## Goals
1. Build a curated list of top AI companies with metadata (funding, products, headcount)
2. Crawl their career/jobs pages — focus ONLY on Research Engineer and ML Engineer roles (including variants: "Machine Learning Engineer", "ML Scientist", "Research Scientist", "Applied Scientist", "ML Infrastructure Engineer", "Applied ML Engineer")
3. For each matching role, crawl the job detail page and extract **requirements**: years of experience, degree level, specific skills (PyTorch, TensorFlow, distributed training, CUDA, etc.), publication expectations, programming languages
4. Normalize all data into structured storage (SQLite + JSONL)
5. Analyze what top AI companies require for ML/Research roles — compare requirements across companies, identify common vs rare skills, seniority expectations
6. Generate charts visualizing the ML/Research job landscape

## Tech Stack
- Python 3.11+
- requests + BeautifulSoup4 (crawling)
- sqlite3 (storage)
- pandas (data processing)
- matplotlib + plotly (visualization)
- pybloom_live (dedup, optional)

## Directory Structure
```
AIJobCrawler/
  crawler.py          # Base crawler class (already exists)
  companies.py        # Company list and metadata
  job_crawler.py      # Career page crawlers — filters for ML/Research roles only
  role_parser.py      # Parse individual job detail pages for requirements
  company_crawler.py  # Company info crawlers
  db.py               # SQLite schema and helpers (companies, roles, requirements tables)
  analyze.py          # Requirements analysis and cross-company comparison
  charts.py           # Chart generation (skill freq, degree dist, requirements heatmap)
  config.py           # Configuration constants
  main.py             # CLI entrypoint
  data/               # Raw crawled data (JSONL)
  output/             # Generated charts and reports
  tests/              # Test files
```

## Coding Conventions
- Use type hints on all function signatures
- One module per concern (crawling, storage, analysis, visualization)
- All crawled data goes through db.py for storage
- Respect rate limits: minimum 1s delay between requests to same domain
- User-Agent must identify as a bot for ethical crawling
- Handle errors gracefully — log and continue, don't crash the pipeline

## Overnight Batch Run
- Task tracking: tasks.json
- Cross-session memory: progress.md
- **Always read progress.md before starting any work**
