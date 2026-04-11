"""Tests for TalentDiscovery with mocked GoogleSearchClient."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3
import pytest

from db import init_db
from talent_discovery import TalentDiscovery


class FakeSearchClient:
    def __init__(self, responses: dict[str, list[dict]]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def search(self, query: str, num: int = 10) -> list[dict]:
        self.calls.append(query)
        # match first key that is a substring of query, else []
        for key, resp in self.responses.items():
            if key in query:
                return resp
        return []


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c
    c.close()


def test_discover_lab_stores_profiles(conn):
    fake = FakeSearchClient(
        {
            "OpenAI": [
                {
                    "title": "Jane Doe - Research Scientist at Sunday Robotics | LinkedIn",
                    "url": "https://linkedin.com/in/janedoe",
                    "snippet": "Former Research Scientist at OpenAI.",
                },
                {
                    "title": "John Smith - ML Engineer at Project Prometheus | LinkedIn",
                    "url": "https://linkedin.com/in/jsmith",
                    "snippet": "ex-OpenAI.",
                },
            ]
        }
    )
    td = TalentDiscovery(conn, client=fake)
    stored = td.discover_lab("OpenAI", ["OpenAI"], max_queries=1)
    assert stored == 2
    rows = conn.execute("SELECT * FROM talent_moves").fetchall()
    assert len(rows) == 2
    assert td.stats["queries_run"] == 1
    assert td.stats["profiles_found"] == 2
    assert td.stats["profiles_stored"] == 2


def test_self_reference_skipped(conn):
    fake = FakeSearchClient(
        {
            "Anthropic": [
                {
                    "title": "Still Here - Research Scientist at Anthropic | LinkedIn",
                    "url": "https://linkedin.com/in/stillhere",
                    "snippet": "Research Scientist.",
                },
                {
                    "title": "Moved On - ML Engineer at New Co | LinkedIn",
                    "url": "https://linkedin.com/in/movedon",
                    "snippet": "ex-Anthropic.",
                },
            ]
        }
    )
    td = TalentDiscovery(conn, client=fake)
    td.discover_lab("Anthropic", ["Anthropic"], max_queries=1)
    rows = conn.execute("SELECT person_name FROM talent_moves").fetchall()
    assert len(rows) == 1
    assert rows[0]["person_name"] == "Moved On"


def test_non_profile_urls_skipped(conn):
    fake = FakeSearchClient(
        {
            "xAI": [
                {"title": "xAI Company Page", "url": "https://linkedin.com/company/xai", "snippet": ""},
                {"title": "", "url": "https://linkedin.com/in/nobody", "snippet": ""},
            ]
        }
    )
    td = TalentDiscovery(conn, client=fake)
    td.discover_lab("xAI", ["xAI"], max_queries=1)
    rows = conn.execute("SELECT * FROM talent_moves").fetchall()
    assert len(rows) == 0


def test_duplicate_linkedin_url_ignored(conn):
    fake = FakeSearchClient(
        {
            "OpenAI": [
                {
                    "title": "Jane Doe - Research Scientist at Sunday Robotics | LinkedIn",
                    "url": "https://linkedin.com/in/janedoe",
                    "snippet": "Former at OpenAI.",
                },
                {
                    "title": "Jane Doe - Research Scientist at Sunday Robotics | LinkedIn",
                    "url": "https://linkedin.com/in/janedoe",
                    "snippet": "Former at OpenAI.",
                },
            ]
        }
    )
    td = TalentDiscovery(conn, client=fake)
    td.discover_lab("OpenAI", ["OpenAI"], max_queries=1)
    rows = conn.execute("SELECT * FROM talent_moves").fetchall()
    assert len(rows) == 1


def test_discover_all_iterates_labs(conn, monkeypatch):
    import talent_discovery as td_mod

    monkeypatch.setattr(
        td_mod,
        "SOURCE_LABS",
        [
            {"name": "LabA", "queries": ["LabA"]},
            {"name": "LabB", "queries": ["LabB"]},
        ],
    )
    fake = FakeSearchClient(
        {
            "LabA": [
                {"title": "A1 - RE at CoA | LinkedIn", "url": "https://linkedin.com/in/a1", "snippet": "ex-LabA"},
            ],
            "LabB": [
                {"title": "B1 - MLE at CoB | LinkedIn", "url": "https://linkedin.com/in/b1", "snippet": "ex-LabB"},
            ],
        }
    )
    td = td_mod.TalentDiscovery(conn, client=fake)
    stats = td.discover_all(max_queries_per_lab=1)
    assert stats["profiles_stored"] == 2
