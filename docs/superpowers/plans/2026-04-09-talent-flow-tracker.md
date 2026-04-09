# Talent Flow Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discover promising AI companies by tracking where top-lab alumni move to via LinkedIn search, then crawl their ML/Research Engineer openings and produce a ranked summary.

**Architecture:** Google/Bing `site:linkedin.com/in` searches find ex-lab employees and their current companies. Results are aggregated, enriched with company metadata via web search, then fed into the existing job crawling pipeline. Final output is a markdown tracker ranking companies by talent signal with role details.

**Tech Stack:** Python 3.11, requests, BeautifulSoup4, sqlite3, pandas, matplotlib, plotly, Google Custom Search API (free tier)

**Dependency:** Iteration 1 (tasks 1-22) must complete first — provides db.py, config.py, job_crawler.py, role_parser.py, analyze.py, charts.py.

---

### Task 1: Google Custom Search API Setup & Config

**Files:**
- Modify: `config.py` (add search API constants, source labs list)
- Create: `search_client.py`
- Create: `tests/test_search_client.py`

- [ ] **Step 1: Write failing test for search client**

```python
# tests/test_search_client.py
import pytest
from unittest.mock import patch, MagicMock
from search_client import GoogleSearchClient

def test_search_returns_parsed_results():
    mock_response = {
        "items": [
            {
                "title": "John Doe - Staff ML Engineer at CoolStartup | LinkedIn",
                "link": "https://www.linkedin.com/in/johndoe/",
                "snippet": "Previously: Research Scientist at OpenAI. Now building next-gen AI at CoolStartup."
            }
        ]
    }
    with patch("search_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        client = GoogleSearchClient(api_key="test", cx="test")
        results = client.search("site:linkedin.com/in ex-OpenAI")
        assert len(results) == 1
        assert results[0]["title"] == "John Doe - Staff ML Engineer at CoolStartup | LinkedIn"
        assert results[0]["url"] == "https://www.linkedin.com/in/johndoe/"
        assert "OpenAI" in results[0]["snippet"]

def test_search_handles_empty_response():
    with patch("search_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {})
        client = GoogleSearchClient(api_key="test", cx="test")
        results = client.search("site:linkedin.com/in ex-OpenAI")
        assert results == []

def test_search_handles_rate_limit():
    with patch("search_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=429)
        client = GoogleSearchClient(api_key="test", cx="test")
        results = client.search("site:linkedin.com/in ex-OpenAI")
        assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_search_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'search_client'`

- [ ] **Step 3: Add source labs and search config to config.py**

Append to existing `config.py`:

```python
# --- Iteration 2: Talent Flow ---

GOOGLE_API_KEY = ""  # Set via env var GOOGLE_API_KEY
GOOGLE_CX = ""       # Set via env var GOOGLE_CX (Custom Search Engine ID)

SOURCE_LABS = [
    {"name": "OpenAI", "queries": ["OpenAI"]},
    {"name": "Anthropic", "queries": ["Anthropic"]},
    {"name": "Google DeepMind", "queries": ["Google DeepMind", "DeepMind"]},
    {"name": "Meta FAIR", "queries": ["Meta FAIR", "Facebook AI Research"]},
    {"name": "xAI", "queries": ["xAI"]},
    {"name": "Mistral", "queries": ["Mistral AI", "Mistral"]},
    {"name": "Cohere", "queries": ["Cohere"]},
    {"name": "AI21 Labs", "queries": ["AI21 Labs", "AI21"]},
    {"name": "Inflection AI", "queries": ["Inflection AI", "Inflection"]},
    {"name": "Stability AI", "queries": ["Stability AI"]},
    {"name": "Character.ai", "queries": ["Character.ai", "Character AI"]},
    {"name": "Adept", "queries": ["Adept AI", "Adept"]},
    {"name": "Amazon AGI", "queries": ["Amazon AGI", "AWS AI"]},
    {"name": "Apple ML", "queries": ["Apple Machine Learning", "Apple ML"]},
    {"name": "Microsoft Research AI", "queries": ["Microsoft Research", "MSR AI"]},
    {"name": "NVIDIA Research", "queries": ["NVIDIA Research", "NVIDIA AI"]},
    {"name": "Baidu AI", "queries": ["Baidu Research", "Baidu AI"]},
    {"name": "ByteDance AI", "queries": ["ByteDance AI", "TikTok AI"]},
    {"name": "Samsung AI", "queries": ["Samsung AI", "Samsung Research"]},
    {"name": "Alibaba DAMO", "queries": ["Alibaba DAMO", "DAMO Academy"]},
]

SEARCH_QUERY_TEMPLATES = [
    'site:linkedin.com/in "ex-{query}"',
    'site:linkedin.com/in "formerly at {query}"',
    'site:linkedin.com/in "{query}" "former"',
    'site:linkedin.com/in "previously at {query}"',
]

SEARCH_RATE_LIMIT_DELAY = 1.5  # seconds between API calls
SEARCH_MAX_RESULTS_PER_QUERY = 10
```

- [ ] **Step 4: Implement search_client.py**

```python
# search_client.py
"""Google Custom Search API client for LinkedIn profile discovery."""
import os
import time
import logging
import requests
from typing import list

logger = logging.getLogger(__name__)

class GoogleSearchClient:
    """Thin wrapper around Google Custom Search JSON API (free tier: 100/day)."""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str | None = None, cx: str | None = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.cx = cx or os.environ.get("GOOGLE_CX", "")
        self.last_request_time = 0.0
        self.daily_count = 0

    def search(self, query: str, num: int = 10) -> list[dict]:
        """Run a search query. Returns list of {title, url, snippet} dicts."""
        if not self.api_key or not self.cx:
            logger.warning("Google API key or CX not set. Returning empty.")
            return []

        # Rate limit
        elapsed = time.time() - self.last_request_time
        if elapsed < 1.5:
            time.sleep(1.5 - elapsed)

        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(num, 10),
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            self.last_request_time = time.time()
            self.daily_count += 1

            if resp.status_code == 429:
                logger.warning("Rate limited by Google. Stopping.")
                return []
            if resp.status_code != 200:
                logger.error(f"Google search failed: {resp.status_code}")
                return []

            data = resp.json()
            items = data.get("items", [])
            return [
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                }
                for item in items
            ]
        except requests.RequestException as e:
            logger.error(f"Search request failed: {e}")
            return []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_search_client.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add config.py search_client.py tests/test_search_client.py
git commit -m "feat: add Google Custom Search client and source labs config"
```

---

### Task 2: DB Schema for Talent Flow

**Files:**
- Modify: `db.py` (add talent_moves and company_discovery tables)
- Create: `tests/test_db_talent.py`

- [ ] **Step 1: Write failing test for new tables**

```python
# tests/test_db_talent.py
import sqlite3
import pytest
from db import get_connection, init_db, insert_talent_move, insert_discovered_company, get_talent_moves_by_lab, get_top_companies_by_talent

@pytest.fixture
def db():
    conn = get_connection(":memory:")
    init_db(conn)
    yield conn
    conn.close()

def test_insert_and_query_talent_move(db):
    insert_talent_move(db, {
        "person_name": "Jane Doe",
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "previous_lab": "OpenAI",
        "previous_title": "Research Scientist",
        "current_company": "Project Prometheus",
        "current_title": "Senior Research Engineer",
        "source_query": 'site:linkedin.com/in "ex-OpenAI"',
    })
    moves = get_talent_moves_by_lab(db, "OpenAI")
    assert len(moves) == 1
    assert moves[0]["current_company"] == "Project Prometheus"

def test_dedup_talent_move_by_linkedin_url(db):
    move = {
        "person_name": "Jane Doe",
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "previous_lab": "OpenAI",
        "previous_title": "Research Scientist",
        "current_company": "Project Prometheus",
        "current_title": "Senior Research Engineer",
        "source_query": "test",
    }
    insert_talent_move(db, move)
    insert_talent_move(db, move)  # duplicate — should not crash
    moves = get_talent_moves_by_lab(db, "OpenAI")
    assert len(moves) == 1

def test_insert_and_query_discovered_company(db):
    insert_discovered_company(db, {
        "company_name": "Project Prometheus",
        "talent_count": 5,
        "talent_sources": '{"OpenAI": 3, "FAIR": 2}',
        "category": "foundation-model",
    })
    companies = get_top_companies_by_talent(db, limit=10)
    assert len(companies) == 1
    assert companies[0]["company_name"] == "Project Prometheus"
    assert companies[0]["talent_count"] == 5

def test_top_companies_sorted_by_talent(db):
    insert_discovered_company(db, {"company_name": "SmallCo", "talent_count": 2, "talent_sources": "{}", "category": "stealth"})
    insert_discovered_company(db, {"company_name": "BigCo", "talent_count": 10, "talent_sources": "{}", "category": "foundation-model"})
    companies = get_top_companies_by_talent(db, limit=10)
    assert companies[0]["company_name"] == "BigCo"
    assert companies[1]["company_name"] == "SmallCo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_db_talent.py -v`
Expected: FAIL — `ImportError: cannot import name 'insert_talent_move' from 'db'`

- [ ] **Step 3: Add talent tables and helper functions to db.py**

Append to existing `db.py` (after the existing `init_db` function's table creates):

```python
# --- Talent Flow tables (Iteration 2) ---

def _init_talent_tables(conn: sqlite3.Connection) -> None:
    """Create talent_moves and company_discovery tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS talent_moves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_name TEXT NOT NULL,
            linkedin_url TEXT UNIQUE NOT NULL,
            previous_lab TEXT NOT NULL,
            previous_title TEXT DEFAULT '',
            current_company TEXT NOT NULL,
            current_title TEXT DEFAULT '',
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_query TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS company_discovery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            talent_count INTEGER DEFAULT 0,
            talent_sources TEXT DEFAULT '{}',
            category TEXT DEFAULT 'unknown',
            funding TEXT DEFAULT '',
            founded TEXT DEFAULT '',
            hq_location TEXT DEFAULT '',
            careers_url TEXT DEFAULT '',
            website TEXT DEFAULT '',
            description TEXT DEFAULT '',
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            enriched BOOLEAN DEFAULT 0,
            added_to_pipeline BOOLEAN DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_talent_lab ON talent_moves(previous_lab);
        CREATE INDEX IF NOT EXISTS idx_talent_company ON talent_moves(current_company);
        CREATE INDEX IF NOT EXISTS idx_discovery_talent ON company_discovery(talent_count DESC);
    """)

def insert_talent_move(conn: sqlite3.Connection, move: dict) -> None:
    """Insert a talent move, ignoring duplicates by linkedin_url."""
    conn.execute(
        """INSERT OR IGNORE INTO talent_moves
           (person_name, linkedin_url, previous_lab, previous_title, current_company, current_title, source_query)
           VALUES (:person_name, :linkedin_url, :previous_lab, :previous_title, :current_company, :current_title, :source_query)""",
        move,
    )
    conn.commit()

def insert_discovered_company(conn: sqlite3.Connection, company: dict) -> None:
    """Insert or update a discovered company."""
    conn.execute(
        """INSERT OR REPLACE INTO company_discovery
           (company_name, talent_count, talent_sources, category)
           VALUES (:company_name, :talent_count, :talent_sources, :category)""",
        company,
    )
    conn.commit()

def get_talent_moves_by_lab(conn: sqlite3.Connection, lab: str) -> list[dict]:
    """Get all talent moves from a specific source lab."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM talent_moves WHERE previous_lab = ?", (lab,)).fetchall()
    return [dict(r) for r in rows]

def get_top_companies_by_talent(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    """Get companies ranked by talent inflow count."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM company_discovery ORDER BY talent_count DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
```

Also add `_init_talent_tables(conn)` call at the end of the existing `init_db` function.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_db_talent.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add db.py tests/test_db_talent.py
git commit -m "feat: add talent_moves and company_discovery DB tables"
```

---

### Task 3: Profile Parser

**Files:**
- Create: `profile_parser.py`
- Create: `tests/test_profile_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_profile_parser.py
import pytest
from profile_parser import parse_search_result

def test_parse_standard_linkedin_title():
    result = {
        "title": "John Smith - Senior Research Engineer at Project Prometheus | LinkedIn",
        "url": "https://www.linkedin.com/in/johnsmith/",
        "snippet": "Previously: Research Scientist at OpenAI. Building AI for the physical world."
    }
    parsed = parse_search_result(result, source_lab="OpenAI")
    assert parsed["person_name"] == "John Smith"
    assert parsed["current_company"] == "Project Prometheus"
    assert parsed["current_title"] == "Senior Research Engineer"
    assert parsed["linkedin_url"] == "https://www.linkedin.com/in/johnsmith/"
    assert parsed["previous_lab"] == "OpenAI"

def test_parse_title_with_comma_format():
    """Some titles use 'Name - Title, Company' format."""
    result = {
        "title": "Jane Doe - ML Engineer, Sunday Robotics | LinkedIn",
        "url": "https://www.linkedin.com/in/janedoe/",
        "snippet": "Former OpenAI researcher."
    }
    parsed = parse_search_result(result, source_lab="OpenAI")
    assert parsed["person_name"] == "Jane Doe"
    assert parsed["current_company"] == "Sunday Robotics"
    assert parsed["current_title"] == "ML Engineer"

def test_parse_title_with_at_symbol():
    result = {
        "title": "Neel Kant - Founding Member @ Project Prometheus",
        "url": "https://www.linkedin.com/in/neel-kant/",
        "snippet": "Ex-Google DeepMind."
    }
    parsed = parse_search_result(result, source_lab="Google DeepMind")
    assert parsed["person_name"] == "Neel Kant"
    assert parsed["current_company"] == "Project Prometheus"
    assert parsed["current_title"] == "Founding Member"

def test_parse_unparseable_returns_none():
    result = {
        "title": "LinkedIn",
        "url": "https://www.linkedin.com/company/foo/",
        "snippet": ""
    }
    parsed = parse_search_result(result, source_lab="OpenAI")
    assert parsed is None

def test_parse_strips_linkedin_suffix():
    result = {
        "title": "Alice Wong - Staff MLE at CoolCo | LinkedIn",
        "url": "https://www.linkedin.com/in/alicewong/",
        "snippet": "Formerly at Anthropic."
    }
    parsed = parse_search_result(result, source_lab="Anthropic")
    assert parsed["current_company"] == "CoolCo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_profile_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'profile_parser'`

- [ ] **Step 3: Implement profile_parser.py**

```python
# profile_parser.py
"""Parse Google search result snippets for LinkedIn profile data."""
import re
import logging

logger = logging.getLogger(__name__)

def parse_search_result(result: dict, source_lab: str) -> dict | None:
    """Parse a Google search result into a talent move record.

    Handles LinkedIn title formats:
      - "Name - Title at Company | LinkedIn"
      - "Name - Title, Company | LinkedIn"
      - "Name - Title @ Company | LinkedIn"
      - "Name - Company | LinkedIn"

    Returns dict with keys: person_name, linkedin_url, previous_lab,
    previous_title, current_company, current_title, source_query.
    Returns None if unparseable.
    """
    title = result.get("title", "")
    url = result.get("url", "")
    snippet = result.get("snippet", "")

    # Must be a personal profile URL
    if "/in/" not in url:
        return None

    # Strip " | LinkedIn" suffix
    title = re.sub(r"\s*\|\s*LinkedIn\s*$", "", title).strip()

    # Split on " - " to get name and role/company
    parts = title.split(" - ", 1)
    if len(parts) < 2:
        return None

    person_name = parts[0].strip()
    role_part = parts[1].strip()

    if not person_name or not role_part:
        return None

    current_title = ""
    current_company = ""

    # Try "Title at Company" or "Title @ Company"
    at_match = re.match(r"(.+?)\s+(?:at|@)\s+(.+)", role_part, re.IGNORECASE)
    if at_match:
        current_title = at_match.group(1).strip()
        current_company = at_match.group(2).strip()
    else:
        # Try "Title, Company"
        comma_match = re.match(r"(.+?),\s+(.+)", role_part)
        if comma_match:
            current_title = comma_match.group(1).strip()
            current_company = comma_match.group(2).strip()
        else:
            # Assume entire role_part is company name
            current_company = role_part

    if not current_company:
        return None

    # Try to extract previous title from snippet
    previous_title = ""
    title_patterns = [
        rf"(?:Previously|Former|Ex)[:\s]+(.+?)\s+at\s+{re.escape(source_lab)}",
        rf"(.+?)\s+at\s+{re.escape(source_lab)}",
    ]
    for pattern in title_patterns:
        m = re.search(pattern, snippet, re.IGNORECASE)
        if m:
            previous_title = m.group(1).strip().rstrip(".")
            break

    return {
        "person_name": person_name,
        "linkedin_url": url,
        "previous_lab": source_lab,
        "previous_title": previous_title,
        "current_company": current_company,
        "current_title": current_title,
        "source_query": "",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_profile_parser.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add profile_parser.py tests/test_profile_parser.py
git commit -m "feat: add LinkedIn search result profile parser"
```

---

### Task 4: Talent Discovery Pipeline

**Files:**
- Create: `talent_discovery.py`
- Create: `tests/test_talent_discovery.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_talent_discovery.py
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from talent_discovery import TalentDiscovery
from db import get_connection, init_db

@pytest.fixture
def db():
    conn = get_connection(":memory:")
    init_db(conn)
    yield conn
    conn.close()

def test_discover_from_one_lab(db):
    mock_results = [
        {
            "title": "Alice - Senior RE at CoolStartup | LinkedIn",
            "url": "https://www.linkedin.com/in/alice/",
            "snippet": "Former Research Scientist at OpenAI."
        },
        {
            "title": "Bob - ML Engineer at AnotherCo | LinkedIn",
            "url": "https://www.linkedin.com/in/bob/",
            "snippet": "Previously at OpenAI."
        },
    ]
    with patch("talent_discovery.GoogleSearchClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = mock_results
        instance.daily_count = 0

        td = TalentDiscovery(db)
        td.discover_lab("OpenAI", queries=["OpenAI"], max_queries=1)

    from db import get_talent_moves_by_lab
    moves = get_talent_moves_by_lab(db, "OpenAI")
    assert len(moves) == 2
    companies = {m["current_company"] for m in moves}
    assert "CoolStartup" in companies
    assert "AnotherCo" in companies

def test_discover_skips_self_referencing(db):
    """If someone's current company is the same as source lab, skip."""
    mock_results = [
        {
            "title": "Carol - Researcher at OpenAI | LinkedIn",
            "url": "https://www.linkedin.com/in/carol/",
            "snippet": "At OpenAI since 2020."
        },
    ]
    with patch("talent_discovery.GoogleSearchClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = mock_results
        instance.daily_count = 0

        td = TalentDiscovery(db)
        td.discover_lab("OpenAI", queries=["OpenAI"], max_queries=1)

    from db import get_talent_moves_by_lab
    moves = get_talent_moves_by_lab(db, "OpenAI")
    assert len(moves) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_talent_discovery.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'talent_discovery'`

- [ ] **Step 3: Implement talent_discovery.py**

```python
# talent_discovery.py
"""Discover where top-lab alumni go by searching LinkedIn profiles via Google."""
import logging
import sqlite3
from search_client import GoogleSearchClient
from profile_parser import parse_search_result
from db import insert_talent_move
from config import SOURCE_LABS, SEARCH_QUERY_TEMPLATES

logger = logging.getLogger(__name__)

class TalentDiscovery:
    """Runs search queries for each source lab, parses results, stores talent moves."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.client = GoogleSearchClient()
        self.stats = {"queries": 0, "profiles_found": 0, "profiles_stored": 0}

    def discover_lab(self, lab_name: str, queries: list[str], max_queries: int | None = None) -> None:
        """Run all query templates for one lab's query variants."""
        query_count = 0
        for query_term in queries:
            for template in SEARCH_QUERY_TEMPLATES:
                if max_queries and query_count >= max_queries:
                    return
                search_query = template.format(query=query_term)
                logger.info(f"Searching: {search_query}")

                results = self.client.search(search_query)
                self.stats["queries"] += 1
                query_count += 1

                for result in results:
                    self.stats["profiles_found"] += 1
                    parsed = parse_search_result(result, source_lab=lab_name)
                    if parsed is None:
                        continue
                    # Skip if current company matches source lab (still there)
                    if self._is_same_company(parsed["current_company"], lab_name, queries):
                        continue
                    parsed["source_query"] = search_query
                    insert_talent_move(self.conn, parsed)
                    self.stats["profiles_stored"] += 1

        logger.info(f"Lab {lab_name}: {self.stats['profiles_stored']} profiles stored")

    def discover_all(self, max_queries_per_lab: int | None = None) -> None:
        """Run discovery for all source labs."""
        for lab in SOURCE_LABS:
            logger.info(f"Discovering talent from: {lab['name']}")
            self.discover_lab(lab["name"], lab["queries"], max_queries=max_queries_per_lab)
        logger.info(f"Discovery complete. Stats: {self.stats}")

    @staticmethod
    def _is_same_company(current_company: str, lab_name: str, lab_queries: list[str]) -> bool:
        """Check if the person is still at the source lab."""
        current_lower = current_company.lower()
        if lab_name.lower() in current_lower:
            return True
        for q in lab_queries:
            if q.lower() in current_lower:
                return True
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_talent_discovery.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add talent_discovery.py tests/test_talent_discovery.py
git commit -m "feat: add talent discovery pipeline for all source labs"
```

---

### Task 5: Company Aggregation

**Files:**
- Create: `company_aggregator.py`
- Create: `tests/test_company_aggregator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_company_aggregator.py
import json
import sqlite3
import pytest
from db import get_connection, init_db, insert_talent_move, get_top_companies_by_talent
from company_aggregator import aggregate_companies

@pytest.fixture
def db():
    conn = get_connection(":memory:")
    init_db(conn)
    # Seed talent moves
    moves = [
        {"person_name": "A", "linkedin_url": "https://linkedin.com/in/a", "previous_lab": "OpenAI", "previous_title": "", "current_company": "Prometheus", "current_title": "RE", "source_query": ""},
        {"person_name": "B", "linkedin_url": "https://linkedin.com/in/b", "previous_lab": "OpenAI", "previous_title": "", "current_company": "Prometheus", "current_title": "MLE", "source_query": ""},
        {"person_name": "C", "linkedin_url": "https://linkedin.com/in/c", "previous_lab": "Meta FAIR", "previous_title": "", "current_company": "Prometheus", "current_title": "RE", "source_query": ""},
        {"person_name": "D", "linkedin_url": "https://linkedin.com/in/d", "previous_lab": "OpenAI", "previous_title": "", "current_company": "Sunday", "current_title": "MLE", "source_query": ""},
        {"person_name": "E", "linkedin_url": "https://linkedin.com/in/e", "previous_lab": "DeepMind", "previous_title": "", "current_company": "TinyCo", "current_title": "Eng", "source_query": ""},
    ]
    for m in moves:
        insert_talent_move(conn, m)
    yield conn
    conn.close()

def test_aggregate_creates_company_records(db):
    aggregate_companies(db, min_talent=1)
    companies = get_top_companies_by_talent(db, limit=10)
    names = [c["company_name"] for c in companies]
    assert "Prometheus" in names
    assert "Sunday" in names
    assert "TinyCo" in names

def test_aggregate_counts_correct(db):
    aggregate_companies(db, min_talent=1)
    companies = get_top_companies_by_talent(db, limit=10)
    prometheus = next(c for c in companies if c["company_name"] == "Prometheus")
    assert prometheus["talent_count"] == 3
    sources = json.loads(prometheus["talent_sources"])
    assert sources["OpenAI"] == 2
    assert sources["Meta FAIR"] == 1

def test_aggregate_filters_by_min_talent(db):
    aggregate_companies(db, min_talent=2)
    companies = get_top_companies_by_talent(db, limit=10)
    names = [c["company_name"] for c in companies]
    assert "Prometheus" in names
    assert "TinyCo" not in names  # only 1 person
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_company_aggregator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'company_aggregator'`

- [ ] **Step 3: Implement company_aggregator.py**

```python
# company_aggregator.py
"""Aggregate talent moves into company discovery records."""
import json
import logging
import sqlite3
from db import insert_discovered_company

logger = logging.getLogger(__name__)

def aggregate_companies(conn: sqlite3.Connection, min_talent: int = 2) -> list[dict]:
    """Group talent_moves by current_company, create company_discovery records.

    Args:
        conn: SQLite connection
        min_talent: Minimum talent count to include a company

    Returns:
        List of company dicts that were inserted/updated
    """
    rows = conn.execute("""
        SELECT current_company, previous_lab, COUNT(*) as cnt
        FROM talent_moves
        GROUP BY current_company, previous_lab
    """).fetchall()

    # Build company -> {lab: count}
    company_map: dict[str, dict[str, int]] = {}
    for company, lab, cnt in rows:
        if company not in company_map:
            company_map[company] = {}
        company_map[company][lab] = cnt

    inserted = []
    for company_name, sources in company_map.items():
        total = sum(sources.values())
        if total < min_talent:
            continue
        record = {
            "company_name": company_name,
            "talent_count": total,
            "talent_sources": json.dumps(sources),
            "category": "unknown",
        }
        insert_discovered_company(conn, record)
        inserted.append(record)
        logger.info(f"Discovered: {company_name} (talent: {total}, sources: {sources})")

    logger.info(f"Aggregated {len(inserted)} companies with >= {min_talent} talent moves")
    return inserted
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_company_aggregator.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add company_aggregator.py tests/test_company_aggregator.py
git commit -m "feat: add company aggregation from talent moves"
```

---

### Task 6: Company Enricher

**Files:**
- Create: `company_enricher.py`
- Create: `tests/test_company_enricher.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_company_enricher.py
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from db import get_connection, init_db, insert_discovered_company, get_top_companies_by_talent
from company_enricher import enrich_company, enrich_all_companies

@pytest.fixture
def db():
    conn = get_connection(":memory:")
    init_db(conn)
    insert_discovered_company(conn, {
        "company_name": "Project Prometheus",
        "talent_count": 10,
        "talent_sources": '{"OpenAI": 5, "FAIR": 5}',
        "category": "unknown",
    })
    yield conn
    conn.close()

def test_enrich_company_updates_fields(db):
    mock_search_results = [
        {
            "title": "Project Prometheus - AI startup by Jeff Bezos - $6.2B funding",
            "url": "https://techcrunch.com/prometheus",
            "snippet": "Project Prometheus, the $6.2B AI startup founded by Jeff Bezos in San Francisco, focuses on physical-world AI for manufacturing and aerospace. Founded 2025."
        }
    ]
    with patch("company_enricher.GoogleSearchClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = mock_search_results

        enrich_company(db, "Project Prometheus")

    companies = get_top_companies_by_talent(db, limit=10)
    prometheus = companies[0]
    assert prometheus["enriched"] == 1
    assert prometheus["description"] != ""

def test_enrich_skips_already_enriched(db):
    db.execute("UPDATE company_discovery SET enriched = 1 WHERE company_name = 'Project Prometheus'")
    db.commit()

    with patch("company_enricher.GoogleSearchClient") as MockClient:
        instance = MockClient.return_value
        enrich_all_companies(db)
        instance.search.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_company_enricher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'company_enricher'`

- [ ] **Step 3: Implement company_enricher.py**

```python
# company_enricher.py
"""Enrich discovered companies with metadata via web search."""
import re
import logging
import sqlite3
from search_client import GoogleSearchClient

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS = {
    "foundation-model": ["foundation model", "large language model", "llm", "frontier model", "agi"],
    "robotics": ["robot", "humanoid", "embodied", "manipulation"],
    "ai-infra": ["infrastructure", "mlops", "gpu", "compute", "inference", "serving"],
    "ai-app": ["application", "product", "consumer", "enterprise", "saas"],
    "ai-agent": ["agent", "agentic", "autonomous", "copilot", "assistant"],
    "ai-safety": ["safety", "alignment", "interpretability", "governance"],
    "ai-chip": ["chip", "semiconductor", "hardware", "accelerator", "asic"],
}

def _guess_category(text: str) -> str:
    """Guess company category from description text."""
    text_lower = text.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"

def _extract_funding(text: str) -> str:
    """Try to extract funding amount from text."""
    m = re.search(r"\$[\d.]+\s*[BMK](?:illion)?", text, re.IGNORECASE)
    return m.group(0) if m else ""

def _extract_location(text: str) -> str:
    """Try to extract HQ location from text."""
    cities = ["San Francisco", "New York", "London", "Seattle", "Palo Alto",
              "Mountain View", "Austin", "Boston", "Zurich", "Paris", "Toronto",
              "Beijing", "Shanghai", "Tel Aviv", "Berlin", "Tokyo"]
    for city in cities:
        if city.lower() in text.lower():
            return city
    return ""

def enrich_company(conn: sqlite3.Connection, company_name: str) -> None:
    """Enrich a single company with web search data."""
    client = GoogleSearchClient()
    results = client.search(f'"{company_name}" AI startup company funding')

    if not results:
        logger.warning(f"No search results for {company_name}")
        conn.execute("UPDATE company_discovery SET enriched = 1 WHERE company_name = ?", (company_name,))
        conn.commit()
        return

    # Combine all snippets for extraction
    all_text = " ".join(r.get("snippet", "") + " " + r.get("title", "") for r in results)
    website = ""
    for r in results:
        url = r.get("url", "")
        if company_name.lower().replace(" ", "") in url.lower().replace(" ", ""):
            website = url
            break

    category = _guess_category(all_text)
    funding = _extract_funding(all_text)
    hq = _extract_location(all_text)
    description = results[0].get("snippet", "")[:500]

    conn.execute("""
        UPDATE company_discovery
        SET category = ?, funding = ?, hq_location = ?, website = ?,
            description = ?, enriched = 1
        WHERE company_name = ?
    """, (category, funding, hq, website, description, company_name))
    conn.commit()
    logger.info(f"Enriched: {company_name} — {category}, {funding}, {hq}")

def enrich_all_companies(conn: sqlite3.Connection) -> None:
    """Enrich all un-enriched discovered companies."""
    rows = conn.execute(
        "SELECT company_name FROM company_discovery WHERE enriched = 0 ORDER BY talent_count DESC"
    ).fetchall()
    for (name,) in rows:
        enrich_company(conn, name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_company_enricher.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add company_enricher.py tests/test_company_enricher.py
git commit -m "feat: add company enricher with web search metadata extraction"
```

---

### Task 7: Tracker Summary Generator

**Files:**
- Create: `tracker.py`
- Create: `tests/test_tracker.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_tracker.py
import json
import sqlite3
import pytest
from db import get_connection, init_db, insert_talent_move, insert_discovered_company
from tracker import generate_tracker_md

@pytest.fixture
def db():
    conn = get_connection(":memory:")
    init_db(conn)
    # Seed data
    insert_discovered_company(conn, {
        "company_name": "Prometheus", "talent_count": 5,
        "talent_sources": '{"OpenAI": 3, "FAIR": 2}',
        "category": "foundation-model",
    })
    conn.execute("""
        UPDATE company_discovery SET funding='$6.2B', hq_location='SF', enriched=1
        WHERE company_name='Prometheus'
    """)
    insert_discovered_company(conn, {
        "company_name": "Sunday", "talent_count": 3,
        "talent_sources": '{"DeepMind": 2, "OpenAI": 1}',
        "category": "robotics",
    })
    conn.execute("""
        UPDATE company_discovery SET funding='$165M', hq_location='SF', enriched=1
        WHERE company_name='Sunday'
    """)
    conn.commit()
    yield conn
    conn.close()

def test_generate_tracker_md_contains_company_table(db):
    md = generate_tracker_md(db)
    assert "Prometheus" in md
    assert "Sunday" in md
    assert "Talent Signal" in md or "Talent Inflow" in md

def test_generate_tracker_md_ranked_by_talent(db):
    md = generate_tracker_md(db)
    prometheus_pos = md.index("Prometheus")
    sunday_pos = md.index("Sunday")
    assert prometheus_pos < sunday_pos  # Prometheus has more talent, should be first
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_tracker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tracker'`

- [ ] **Step 3: Implement tracker.py**

```python
# tracker.py
"""Generate company tracker markdown summary."""
import json
import logging
import sqlite3
from datetime import datetime
from db import get_top_companies_by_talent

logger = logging.getLogger(__name__)

def generate_tracker_md(conn: sqlite3.Connection, output_path: str | None = None) -> str:
    """Generate a ranked markdown summary of discovered companies.

    Args:
        conn: SQLite connection
        output_path: If provided, write to file. Otherwise just return string.

    Returns:
        Markdown string
    """
    companies = get_top_companies_by_talent(conn, limit=100)
    date_str = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# AI Company Tracker — {date_str}",
        "",
        "## Top Companies by Talent Signal",
        "",
        "| Rank | Company | Talent Inflow | Category | Funding | HQ |",
        "|------|---------|---------------|----------|---------|-----|",
    ]

    for i, c in enumerate(companies, 1):
        sources = json.loads(c.get("talent_sources", "{}"))
        source_str = ", ".join(f"{lab}: {cnt}" for lab, cnt in sorted(sources.items(), key=lambda x: -x[1]))
        lines.append(
            f"| {i} | {c['company_name']} | {c['talent_count']} ({source_str}) "
            f"| {c.get('category', 'unknown')} | {c.get('funding', '')} | {c.get('hq_location', '')} |"
        )

    # Stealth section: companies with no website and no funding
    stealth = [c for c in companies if not c.get("website") and not c.get("funding")]
    if stealth:
        lines.extend(["", "## Stealth / Early-Stage (high talent, low public info)", ""])
        for c in stealth:
            sources = json.loads(c.get("talent_sources", "{}"))
            source_str = ", ".join(f"{cnt} ex-{lab}" for lab, cnt in sorted(sources.items(), key=lambda x: -x[1]))
            lines.append(f"- **{c['company_name']}**: {c['talent_count']} people ({source_str})")

    md = "\n".join(lines) + "\n"

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        logger.info(f"Tracker written to {output_path}")

    return md
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_tracker.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add tracker.py tests/test_tracker.py
git commit -m "feat: add tracker summary markdown generator"
```

---

### Task 8: Talent Flow Charts

**Files:**
- Create: `talent_charts.py`
- Create: `tests/test_talent_charts.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_talent_charts.py
import json
import os
import sqlite3
import pytest
from db import get_connection, init_db, insert_talent_move, insert_discovered_company
from talent_charts import generate_sankey, generate_company_ranking_bar, generate_talent_heatmap

@pytest.fixture
def db():
    conn = get_connection(":memory:")
    init_db(conn)
    moves = [
        {"person_name": "A", "linkedin_url": "https://li.com/a", "previous_lab": "OpenAI", "previous_title": "", "current_company": "Prometheus", "current_title": "", "source_query": ""},
        {"person_name": "B", "linkedin_url": "https://li.com/b", "previous_lab": "OpenAI", "previous_title": "", "current_company": "Prometheus", "current_title": "", "source_query": ""},
        {"person_name": "C", "linkedin_url": "https://li.com/c", "previous_lab": "FAIR", "previous_title": "", "current_company": "Prometheus", "current_title": "", "source_query": ""},
        {"person_name": "D", "linkedin_url": "https://li.com/d", "previous_lab": "FAIR", "previous_title": "", "current_company": "Sunday", "current_title": "", "source_query": ""},
    ]
    for m in moves:
        insert_talent_move(conn, m)
    insert_discovered_company(conn, {"company_name": "Prometheus", "talent_count": 3, "talent_sources": '{"OpenAI":2,"FAIR":1}', "category": "foundation-model"})
    insert_discovered_company(conn, {"company_name": "Sunday", "talent_count": 1, "talent_sources": '{"FAIR":1}', "category": "robotics"})
    yield conn
    conn.close()

@pytest.fixture
def output_dir(tmp_path):
    return str(tmp_path)

def test_sankey_creates_html(db, output_dir):
    path = os.path.join(output_dir, "sankey.html")
    generate_sankey(db, path)
    assert os.path.exists(path)
    content = open(path, encoding="utf-8").read()
    assert "plotly" in content.lower() or "Sankey" in content

def test_company_ranking_creates_png(db, output_dir):
    path = os.path.join(output_dir, "ranking.png")
    generate_company_ranking_bar(db, path)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0

def test_heatmap_creates_png(db, output_dir):
    path = os.path.join(output_dir, "heatmap.png")
    generate_talent_heatmap(db, path)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_talent_charts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'talent_charts'`

- [ ] **Step 3: Implement talent_charts.py**

```python
# talent_charts.py
"""Generate talent flow visualizations."""
import json
import logging
import sqlite3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
from db import get_top_companies_by_talent

logger = logging.getLogger(__name__)

def generate_sankey(conn: sqlite3.Connection, output_path: str) -> None:
    """Interactive Sankey diagram: source labs → destination companies."""
    companies = get_top_companies_by_talent(conn, limit=30)

    # Collect all labs and companies
    labs = set()
    flows = []  # (lab, company, count)
    for c in companies:
        sources = json.loads(c.get("talent_sources", "{}"))
        for lab, count in sources.items():
            labs.add(lab)
            flows.append((lab, c["company_name"], count))

    lab_list = sorted(labs)
    company_list = [c["company_name"] for c in companies]
    all_labels = lab_list + company_list

    lab_idx = {name: i for i, name in enumerate(lab_list)}
    company_idx = {name: i + len(lab_list) for i, name in enumerate(company_list)}

    sources_idx = []
    targets_idx = []
    values = []
    for lab, company, count in flows:
        if lab in lab_idx and company in company_idx:
            sources_idx.append(lab_idx[lab])
            targets_idx.append(company_idx[company])
            values.append(count)

    fig = go.Figure(data=[go.Sankey(
        node=dict(label=all_labels, pad=15, thickness=20),
        link=dict(source=sources_idx, target=targets_idx, value=values),
    )])
    fig.update_layout(title_text="AI Talent Flow: Labs → Companies", font_size=12)
    fig.write_html(output_path)
    logger.info(f"Sankey saved to {output_path}")

def generate_company_ranking_bar(conn: sqlite3.Connection, output_path: str) -> None:
    """Horizontal bar chart: companies ranked by talent inflow."""
    companies = get_top_companies_by_talent(conn, limit=30)
    if not companies:
        return

    names = [c["company_name"] for c in reversed(companies)]
    counts = [c["talent_count"] for c in reversed(companies)]

    fig, ax = plt.subplots(figsize=(10, max(6, len(names) * 0.4)))
    bars = ax.barh(names, counts, color="#4A90D9")
    ax.set_xlabel("Ex-Lab Talent Count")
    ax.set_title("AI Companies Ranked by Talent Inflow from Top Labs")
    ax.bar_label(bars, padding=3)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info(f"Company ranking chart saved to {output_path}")

def generate_talent_heatmap(conn: sqlite3.Connection, output_path: str) -> None:
    """Heatmap: source lab × destination company."""
    companies = get_top_companies_by_talent(conn, limit=20)
    if not companies:
        return

    # Collect all labs
    all_labs = set()
    for c in companies:
        sources = json.loads(c.get("talent_sources", "{}"))
        all_labs.update(sources.keys())
    lab_list = sorted(all_labs)
    company_names = [c["company_name"] for c in companies]

    matrix = np.zeros((len(company_names), len(lab_list)))
    for i, c in enumerate(companies):
        sources = json.loads(c.get("talent_sources", "{}"))
        for j, lab in enumerate(lab_list):
            matrix[i][j] = sources.get(lab, 0)

    fig, ax = plt.subplots(figsize=(max(8, len(lab_list) * 0.8), max(6, len(company_names) * 0.5)))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(lab_list)))
    ax.set_xticklabels(lab_list, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(company_names)))
    ax.set_yticklabels(company_names, fontsize=8)
    ax.set_title("Talent Flow Heatmap: Source Lab × Destination Company")

    # Add text annotations
    for i in range(len(company_names)):
        for j in range(len(lab_list)):
            val = int(matrix[i][j])
            if val > 0:
                ax.text(j, i, str(val), ha="center", va="center", fontsize=7)

    plt.colorbar(im, ax=ax, label="People")
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info(f"Talent heatmap saved to {output_path}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_talent_charts.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add talent_charts.py tests/test_talent_charts.py
git commit -m "feat: add talent flow charts (sankey, ranking bar, heatmap)"
```

---

### Task 9: CLI Integration — Add Iteration 2 Commands to main.py

**Files:**
- Modify: `main.py` (add `discover`, `enrich`, `track` subcommands)
- Create: `tests/test_main_iter2.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_main_iter2.py
import subprocess
import sys

def test_main_discover_help():
    result = subprocess.run(
        [sys.executable, "main.py", "discover", "--help"],
        capture_output=True, text=True, cwd="C:/Users/RR/Documents/Projects/AIJobCrawler"
    )
    assert result.returncode == 0
    assert "discover" in result.stdout.lower() or "talent" in result.stdout.lower()

def test_main_track_help():
    result = subprocess.run(
        [sys.executable, "main.py", "track", "--help"],
        capture_output=True, text=True, cwd="C:/Users/RR/Documents/Projects/AIJobCrawler"
    )
    assert result.returncode == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_main_iter2.py -v`
Expected: FAIL (either main.py doesn't exist yet or doesn't have discover subcommand)

- [ ] **Step 3: Add iteration 2 subcommands to main.py**

Add these subcommands to the existing argparse setup in `main.py`:

```python
# Add to existing main.py argparse subparsers:

# --- Iteration 2 commands ---
discover_parser = subparsers.add_parser("discover", help="Discover companies via LinkedIn talent flow search")
discover_parser.add_argument("--max-queries-per-lab", type=int, default=None,
                             help="Limit queries per source lab (for testing)")
discover_parser.add_argument("--min-talent", type=int, default=2,
                             help="Minimum talent count to include a company (default: 2)")

enrich_parser = subparsers.add_parser("enrich", help="Enrich discovered companies with metadata via web search")

track_parser = subparsers.add_parser("track", help="Generate company tracker summary and charts")
track_parser.add_argument("--output-dir", type=str, default="output",
                          help="Output directory for tracker files")

pipeline_parser = subparsers.add_parser("discover-all",
    help="Run full discovery pipeline: discover → aggregate → enrich → track")
pipeline_parser.add_argument("--max-queries-per-lab", type=int, default=None)
pipeline_parser.add_argument("--min-talent", type=int, default=2)

# Add to the command dispatch:
def cmd_discover(args):
    from db import get_connection, init_db
    from talent_discovery import TalentDiscovery
    from company_aggregator import aggregate_companies
    conn = get_connection("data/aijobs.db")
    init_db(conn)
    td = TalentDiscovery(conn)
    td.discover_all(max_queries_per_lab=args.max_queries_per_lab)
    aggregate_companies(conn, min_talent=args.min_talent)
    print(f"Discovery complete. Stats: {td.stats}")
    conn.close()

def cmd_enrich(args):
    from db import get_connection, init_db
    from company_enricher import enrich_all_companies
    conn = get_connection("data/aijobs.db")
    init_db(conn)
    enrich_all_companies(conn)
    conn.close()

def cmd_track(args):
    import os
    from db import get_connection, init_db
    from tracker import generate_tracker_md
    from talent_charts import generate_sankey, generate_company_ranking_bar, generate_talent_heatmap
    conn = get_connection("data/aijobs.db")
    init_db(conn)
    os.makedirs(args.output_dir, exist_ok=True)
    generate_tracker_md(conn, os.path.join(args.output_dir, "company_tracker.md"))
    generate_sankey(conn, os.path.join(args.output_dir, "talent_flow_sankey.html"))
    generate_company_ranking_bar(conn, os.path.join(args.output_dir, "company_ranking.png"))
    generate_talent_heatmap(conn, os.path.join(args.output_dir, "talent_heatmap.png"))
    print(f"Tracker output written to {args.output_dir}/")
    conn.close()

def cmd_discover_all(args):
    cmd_discover(args)
    cmd_enrich(args)
    cmd_track(args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_main_iter2.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add main.py tests/test_main_iter2.py
git commit -m "feat: add discover/enrich/track CLI commands for talent flow pipeline"
```

---

### Task 10: Integration — Feed Discovered Companies Into Job Crawler

**Files:**
- Create: `pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_pipeline.py
import sqlite3
import pytest
from db import get_connection, init_db, insert_discovered_company
from pipeline import get_companies_for_crawling, mark_company_crawled

@pytest.fixture
def db():
    conn = get_connection(":memory:")
    init_db(conn)
    insert_discovered_company(conn, {
        "company_name": "Prometheus", "talent_count": 5,
        "talent_sources": '{}', "category": "foundation-model",
    })
    conn.execute("""
        UPDATE company_discovery SET careers_url='https://boards.greenhouse.io/prometheus/jobs',
        enriched=1 WHERE company_name='Prometheus'
    """)
    conn.commit()
    yield conn
    conn.close()

def test_get_companies_for_crawling(db):
    companies = get_companies_for_crawling(db)
    assert len(companies) == 1
    assert companies[0]["company_name"] == "Prometheus"
    assert companies[0]["careers_url"] != ""

def test_mark_company_crawled(db):
    mark_company_crawled(db, "Prometheus")
    companies = get_companies_for_crawling(db)
    assert len(companies) == 0  # already crawled
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline'`

- [ ] **Step 3: Implement pipeline.py**

```python
# pipeline.py
"""Bridge between talent-flow discovery and job crawling pipeline."""
import logging
import sqlite3

logger = logging.getLogger(__name__)

def get_companies_for_crawling(conn: sqlite3.Connection) -> list[dict]:
    """Get discovered companies that have careers URLs but haven't been crawled yet."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM company_discovery
        WHERE enriched = 1
          AND careers_url != ''
          AND added_to_pipeline = 0
        ORDER BY talent_count DESC
    """).fetchall()
    return [dict(r) for r in rows]

def mark_company_crawled(conn: sqlite3.Connection, company_name: str) -> None:
    """Mark a company as added to the crawling pipeline."""
    conn.execute(
        "UPDATE company_discovery SET added_to_pipeline = 1 WHERE company_name = ?",
        (company_name,),
    )
    conn.commit()

def run_full_pipeline(conn: sqlite3.Connection) -> None:
    """Run the complete pipeline: discovered companies → job crawl → tracker update."""
    from job_crawler import JobCrawler
    from tracker import generate_tracker_md
    from talent_charts import generate_sankey, generate_company_ranking_bar, generate_talent_heatmap

    companies = get_companies_for_crawling(conn)
    logger.info(f"Found {len(companies)} companies to crawl for jobs")

    crawler = JobCrawler(conn)
    for company in companies:
        logger.info(f"Crawling jobs for: {company['company_name']} ({company['careers_url']})")
        try:
            crawler.crawl_company(company["company_name"], company["careers_url"])
            mark_company_crawled(conn, company["company_name"])
        except Exception as e:
            logger.error(f"Failed to crawl {company['company_name']}: {e}")

    # Regenerate outputs
    generate_tracker_md(conn, "output/company_tracker.md")
    generate_sankey(conn, "output/talent_flow_sankey.html")
    generate_company_ranking_bar(conn, "output/company_ranking.png")
    generate_talent_heatmap(conn, "output/talent_heatmap.png")
    logger.info("Full pipeline complete. Outputs updated.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_pipeline.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add pipeline.py tests/test_pipeline.py
git commit -m "feat: add pipeline bridge from talent discovery to job crawling"
```

---

### Task 11: End-to-End Smoke Test

**Files:**
- Create: `tests/test_e2e_iter2.py`

- [ ] **Step 1: Write e2e test**

```python
# tests/test_e2e_iter2.py
"""End-to-end test: full iteration 2 pipeline with mocked search results."""
import json
import os
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from db import get_connection, init_db, get_top_companies_by_talent, get_talent_moves_by_lab
from talent_discovery import TalentDiscovery
from company_aggregator import aggregate_companies
from company_enricher import enrich_all_companies
from tracker import generate_tracker_md

MOCK_SEARCH_RESULTS = {
    "talent": [
        {"title": "Alice - Senior RE at Prometheus | LinkedIn", "url": "https://linkedin.com/in/alice", "snippet": "Former Research Scientist at OpenAI."},
        {"title": "Bob - MLE at Prometheus | LinkedIn", "url": "https://linkedin.com/in/bob", "snippet": "Previously at Meta FAIR."},
        {"title": "Carol - Staff Eng at Sunday | LinkedIn", "url": "https://linkedin.com/in/carol", "snippet": "Ex-OpenAI."},
        {"title": "Dan - RE at NewCo | LinkedIn", "url": "https://linkedin.com/in/dan", "snippet": "Formerly at Google DeepMind."},
        {"title": "Eve - Researcher at NewCo | LinkedIn", "url": "https://linkedin.com/in/eve", "snippet": "Previously at Anthropic."},
    ],
    "enrich": [
        {"title": "Prometheus AI startup - $6.2B", "url": "https://prometheus.ai", "snippet": "Foundation model company in San Francisco."},
    ],
}

@pytest.fixture
def db():
    conn = get_connection(":memory:")
    init_db(conn)
    yield conn
    conn.close()

def test_full_pipeline(db, tmp_path):
    # Step 1: Discover
    call_count = {"n": 0}
    def mock_search(query, num=10):
        call_count["n"] += 1
        return MOCK_SEARCH_RESULTS["talent"]

    with patch("talent_discovery.GoogleSearchClient") as MockClient:
        instance = MockClient.return_value
        instance.search.side_effect = mock_search
        instance.daily_count = 0

        td = TalentDiscovery(db)
        td.discover_lab("OpenAI", queries=["OpenAI"], max_queries=1)
        td.discover_lab("Meta FAIR", queries=["Meta FAIR"], max_queries=1)

    # Step 2: Aggregate
    aggregate_companies(db, min_talent=1)
    companies = get_top_companies_by_talent(db, limit=10)
    assert len(companies) >= 2  # Prometheus and NewCo at minimum

    # Step 3: Enrich
    with patch("company_enricher.GoogleSearchClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = MOCK_SEARCH_RESULTS["enrich"]
        enrich_all_companies(db)

    # Step 4: Generate tracker
    output_path = str(tmp_path / "tracker.md")
    md = generate_tracker_md(db, output_path)
    assert os.path.exists(output_path)
    assert "Prometheus" in md
    assert "Talent" in md
```

- [ ] **Step 2: Run test**

Run: `cd C:/Users/RR/Documents/Projects/AIJobCrawler && python -m pytest tests/test_e2e_iter2.py -v`
Expected: 1 passed

- [ ] **Step 3: Fix any failures and re-run until green**

- [ ] **Step 4: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add tests/test_e2e_iter2.py
git commit -m "test: add end-to-end smoke test for talent flow pipeline"
```

---

### Task 12: Google Custom Search API Setup Instructions

**Files:**
- Create: `docs/setup-google-search.md`

- [ ] **Step 1: Write setup guide**

```markdown
# Google Custom Search API Setup (Free Tier)

## 1. Create a Google Cloud Project
- Go to https://console.cloud.google.com/
- Create a new project (or use existing)
- Enable "Custom Search JSON API"

## 2. Get API Key
- Go to APIs & Services → Credentials
- Create an API key
- (Optional) Restrict to Custom Search API only

## 3. Create a Programmable Search Engine
- Go to https://programmablesearchengine.google.com/
- Create new search engine
- Under "Sites to search", add `linkedin.com/in/*`
- Get the Search Engine ID (cx)

## 4. Set Environment Variables

```bash
export GOOGLE_API_KEY="your-api-key-here"
export GOOGLE_CX="your-search-engine-id-here"
```

On Windows (PowerShell):
```powershell
$env:GOOGLE_API_KEY = "your-api-key-here"
$env:GOOGLE_CX = "your-search-engine-id-here"
```

## 5. Free Tier Limits
- 100 queries per day (free)
- 10 results per query
- Enough for ~20 source labs × 5 query variants = 100 queries = 1 day

## 6. Test
```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
python -c "from search_client import GoogleSearchClient; c = GoogleSearchClient(); print(c.search('site:linkedin.com/in ex-OpenAI')[:2])"
```
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/RR/Documents/Projects/AIJobCrawler
git add docs/setup-google-search.md
git commit -m "docs: add Google Custom Search API setup guide"
```

---

## Summary

| Task | Module | Description |
|------|--------|-------------|
| 1 | `search_client.py`, `config.py` | Google Custom Search API client + source labs config |
| 2 | `db.py` | talent_moves + company_discovery DB tables |
| 3 | `profile_parser.py` | Parse LinkedIn search snippets for name/company/title |
| 4 | `talent_discovery.py` | Run searches for all 20 source labs, store talent moves |
| 5 | `company_aggregator.py` | Group moves by company, rank by talent count |
| 6 | `company_enricher.py` | Web search to fill in funding/category/HQ/website |
| 7 | `tracker.py` | Generate company_tracker.md ranked summary |
| 8 | `talent_charts.py` | Sankey, ranking bar chart, heatmap |
| 9 | `main.py` | CLI subcommands: discover, enrich, track, discover-all |
| 10 | `pipeline.py` | Bridge: feed discovered companies into job crawler |
| 11 | `tests/test_e2e_iter2.py` | End-to-end smoke test |
| 12 | `docs/setup-google-search.md` | API setup instructions |

**Estimated time:** 12 tasks × ~25 min = ~5 hours
