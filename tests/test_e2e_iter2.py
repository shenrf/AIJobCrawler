"""End-to-end smoke test for iteration 2 talent flow pipeline.

Mocks GoogleSearchClient to return fake LinkedIn results across 2 labs.
Runs: discover → aggregate → enrich (mocked) → generate tracker.md.
Verifies everything lands in an in-memory SQLite DB and tracker renders correctly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3
import pytest

from db import init_db
from talent_discovery import TalentDiscovery
from company_aggregator import aggregate_companies
from company_enricher import enrich_all_companies
from tracker import generate_tracker_md


class MockedSearch:
    """Returns different results depending on query substring match."""

    def __init__(self):
        self.responses = {
            "OpenAI": [
                {
                    "title": "Alice Kim - Research Engineer at Sunday Robotics | LinkedIn",
                    "url": "https://linkedin.com/in/alicekim",
                    "snippet": "Former Research Engineer at OpenAI. Working on robotics.",
                },
                {
                    "title": "Bob Lin - Staff MLE at Sunday Robotics | LinkedIn",
                    "url": "https://linkedin.com/in/boblin",
                    "snippet": "ex-OpenAI. Humanoid robots.",
                },
                {
                    "title": "Carol Park - Research Scientist at Stealth AI | LinkedIn",
                    "url": "https://linkedin.com/in/carolpark",
                    "snippet": "Formerly at OpenAI.",
                },
            ],
            "Anthropic": [
                {
                    "title": "Dave Ng - ML Engineer at Sunday Robotics | LinkedIn",
                    "url": "https://linkedin.com/in/daveng",
                    "snippet": "ex-Anthropic.",
                },
                {
                    "title": "Eve Sato - Research Engineer at Stealth AI | LinkedIn",
                    "url": "https://linkedin.com/in/evesato",
                    "snippet": "Formerly at Anthropic. Stealth mode AI startup.",
                },
            ],
            "Sunday Robotics": [
                {
                    "title": "Sunday Robotics $50 million",
                    "url": "https://sundayrobotics.com",
                    "snippet": "Humanoid robot company. $50 million seed. San Francisco.",
                }
            ],
            "Stealth AI": [
                {
                    "title": "Stealth AI",
                    "url": "https://stealth.ai",
                    "snippet": "Emerging AI startup.",
                }
            ],
        }

    def search(self, query: str, num: int = 10) -> list[dict]:
        for key, resp in self.responses.items():
            if key in query:
                return resp
        return []


def test_e2e_pipeline(tmp_path, monkeypatch):
    # In-memory SQLite
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # Pin SOURCE_LABS to 2 labs
    import talent_discovery as td_mod
    monkeypatch.setattr(
        td_mod,
        "SOURCE_LABS",
        [
            {"name": "OpenAI", "queries": ["OpenAI"]},
            {"name": "Anthropic", "queries": ["Anthropic"]},
        ],
    )

    client = MockedSearch()

    # 1. Discover
    td = TalentDiscovery(conn, client=client)
    stats = td.discover_all(max_queries_per_lab=1)
    assert stats["profiles_stored"] >= 5

    moves = conn.execute("SELECT * FROM talent_moves").fetchall()
    assert len(moves) == 5
    labs = {r["previous_lab"] for r in moves}
    assert labs == {"OpenAI", "Anthropic"}

    # 2. Aggregate
    inserted = aggregate_companies(conn, min_talent=2)
    names = {r["company_name"] for r in inserted}
    assert "Sunday Robotics" in names
    assert "Stealth AI" in names

    rows = conn.execute(
        "SELECT * FROM company_discovery ORDER BY talent_count DESC"
    ).fetchall()
    sunday = next(r for r in rows if r["company_name"] == "Sunday Robotics")
    assert sunday["talent_count"] == 3

    # 3. Enrich (mocked)
    count = enrich_all_companies(conn, client=client)
    assert count == 2

    sunday_row = conn.execute(
        "SELECT * FROM company_discovery WHERE company_name='Sunday Robotics'"
    ).fetchone()
    assert sunday_row["enriched"] == 1
    assert sunday_row["funding"] == "$50M"
    assert sunday_row["hq_location"] == "San Francisco"

    # 4. Tracker
    tracker_path = tmp_path / "tracker.md"
    md = generate_tracker_md(conn, tracker_path)
    assert tracker_path.exists()
    assert "Sunday Robotics" in md
    assert "Stealth AI" in md
    # Sunday Robotics (3 talent) should rank above Stealth AI (2 talent)
    assert md.index("Sunday Robotics") < md.index("Stealth AI")

    conn.close()
