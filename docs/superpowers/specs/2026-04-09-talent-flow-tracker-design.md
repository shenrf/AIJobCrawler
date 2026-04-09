# Iteration 2: AI Talent Flow → Company Discovery & Job Tracker

## Goal

Identify promising AI companies by tracking where top-lab alumni go, then crawl their ML/Research Engineer openings and requirements. Produce a ranked summary of companies + roles for manual review.

No automated matching — user reviews the output directly.

## Source Labs (20)

OpenAI, Anthropic, Google DeepMind, Meta FAIR, xAI, Mistral, Cohere, AI21 Labs, Inflection AI, Stability AI, Character.ai, Adept, Amazon AGI, Apple ML, Microsoft Research AI, NVIDIA Research, Baidu AI, ByteDance AI, Samsung AI, Alibaba DAMO

## Data Collection Method

Free-tier only. No LinkedIn login or API keys required.

### Step 1: Talent Discovery (`talent_discovery.py`)

For each source lab, run Google searches:
- `site:linkedin.com/in "ex-{lab}"`
- `site:linkedin.com/in "formerly at {lab}"`
- `site:linkedin.com/in "{lab}" "former"`
- `site:linkedin.com/in "previously at {lab}"`

Parse search result snippets to extract:
- Person name (from result title)
- Current company (from headline/snippet)
- Current title
- LinkedIn profile URL
- Source lab

Rate limits: Google Custom Search API = 100 free queries/day. 20 labs × 4-5 variants = ~100 queries = 1 day. Can supplement with Bing API (1000 free/month).

### Step 2: Company Aggregation (`company_enricher.py`)

From talent_moves data:
1. Group by current_company, count people per company
2. Rank companies by talent inflow (more ex-lab people = stronger signal)
3. For each company (top N or all with 2+ people):
   - Web search for basic info: funding, founding year, headcount, focus area, HQ
   - Auto-categorize: foundation-model / robotics / ai-infra / ai-app / ai-agent / ai-safety / ai-chip / stealth
4. Insert into companies table with `source="talent-flow"`
5. Discover careers page URL via web search or homepage crawl

### Step 3: Job Crawling (existing pipeline)

Feed discovered companies into iteration 1's pipeline:
- `job_crawler.py` crawls career pages, filters for ML/Research Engineer roles
- `role_parser.py` extracts requirements from job detail pages
- Data stored in existing roles + requirements tables

### Step 4: Summary Output

`output/company_tracker.md`:
```
# AI Company Tracker — {date}

## Top Companies by Talent Signal

| Rank | Company | Talent Inflow | Category | Funding | HQ | Open ML/RE Roles |
|------|---------|---------------|----------|---------|----|--------------------|
| 1    | Project Prometheus | 15 (FAIR: 8, DeepMind: 3, OpenAI: 4) | foundation-model | $6.2B | SF | 5 |
| 2    | Sunday Robotics | 8 (OpenAI: 3, DeepMind: 5) | robotics | $165M | SF | 3 |
...

## Role Details

### Project Prometheus
- Senior Research Engineer (SF) — PyTorch, distributed training, 5+ YoE, PhD preferred
- Research Engineer (London) — ML systems, large-scale training, 3+ YoE
...

### Sunday Robotics
- Staff ML Engineer (SF) — robot learning, imitation learning, 7+ YoE
...

## Stealth / Early-Stage (high talent, low public info)
- CompanyX: 4 ex-OpenAI, no website, no funding info
...
```

Additional outputs:
- `output/talent_flow_sankey.html` — interactive Sankey: source labs → destination companies
- `output/company_ranking.png` — horizontal bar: companies by talent count
- `output/talent_heatmap.png` — source lab × destination company heatmap

## New DB Schema

```sql
talent_moves (
    id INTEGER PRIMARY KEY,
    person_name TEXT,
    linkedin_url TEXT UNIQUE,
    previous_lab TEXT,
    previous_title TEXT,
    current_company TEXT,
    current_title TEXT,
    discovered_at TIMESTAMP,
    source_query TEXT
)

company_discovery (
    id INTEGER PRIMARY KEY,
    company_name TEXT UNIQUE,
    talent_count INTEGER,
    talent_sources TEXT,  -- JSON: {"FAIR": 5, "OpenAI": 3}
    category TEXT,
    funding TEXT,
    founded TEXT,
    hq_location TEXT,
    careers_url TEXT,
    website TEXT,
    description TEXT,
    first_seen TIMESTAMP,
    enriched BOOLEAN DEFAULT FALSE,
    added_to_pipeline BOOLEAN DEFAULT FALSE
)
```

## New Modules

| Module | Purpose |
|--------|---------|
| `talent_discovery.py` | Google/Bing site:linkedin.com searches, parse snippets |
| `profile_parser.py` | Extract name/company/title from search result snippets |
| `company_enricher.py` | Web search to enrich discovered companies with metadata |
| `tracker.py` | Generate company_tracker.md summary output |

## Rate Limit Strategy

| API | Free Tier | Usage | Days Needed |
|-----|-----------|-------|-------------|
| Google Custom Search | 100/day | ~100 for talent discovery | 1 |
| Bing Search | 1000/month | supplement + company enrichment | shared |
| Career page crawling | self-hosted | 1s delay per request | 1-2 |
| **Total pipeline** | | | **2-3 days** |

## Dependencies

- Iteration 1 (phases 1-3) must be complete: base crawler, DB, company list, job crawler, role parser
- Iteration 2 adds new modules and feeds into existing pipeline

## Non-Goals

- No automated profile matching or scoring
- No LinkedIn login or authenticated scraping
- No real-time tracking (batch runs, periodic refresh)
- No personal data storage beyond publicly indexed name + career info
