"""Tests for company_enricher."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3
import pytest

from db import init_db, insert_discovered_company
from company_enricher import enrich_company, enrich_all_companies


class FakeClient:
    def __init__(self, responses: dict[str, list[dict]]) -> None:
        self.responses = responses

    def search(self, query: str, num: int = 10) -> list[dict]:
        for key, resp in self.responses.items():
            if key.lower() in query.lower():
                return resp
        return []


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    insert_discovered_company(
        c,
        {
            "company_name": "Sunday Robotics",
            "talent_count": 3,
            "talent_sources": "{}",
            "category": "unknown",
        },
    )
    yield c
    c.close()


def test_enrich_extracts_category_and_funding(conn):
    client = FakeClient(
        {
            "Sunday Robotics": [
                {
                    "title": "Sunday Robotics raises $50 million Series A",
                    "url": "https://sundayrobotics.com",
                    "snippet": "Humanoid robot company based in San Francisco. $50 million seed.",
                }
            ]
        }
    )
    out = enrich_company(conn, "Sunday Robotics", client=client)
    assert out["category"] == "robotics"
    assert out["funding"] == "$50M"
    assert out["hq_location"] == "San Francisco"
    assert out["website"] == "https://sundayrobotics.com"

    row = conn.execute(
        "SELECT * FROM company_discovery WHERE company_name='Sunday Robotics'"
    ).fetchone()
    assert row["enriched"] == 1
    assert row["category"] == "robotics"


def test_billion_funding(conn):
    client = FakeClient(
        {
            "Sunday Robotics": [
                {
                    "title": "Sunday Robotics $2.5 billion Series C",
                    "url": "https://sundayrobotics.com",
                    "snippet": "Robot maker raises $2.5 billion. HQ in Palo Alto.",
                }
            ]
        }
    )
    out = enrich_company(conn, "Sunday Robotics", client=client)
    assert out["funding"] == "$2.5B"
    assert out["hq_location"] == "Palo Alto"


def test_enrich_all_skips_already_enriched(conn):
    # Mark as enriched already
    conn.execute(
        "UPDATE company_discovery SET enriched = 1 WHERE company_name = 'Sunday Robotics'"
    )
    conn.commit()
    client = FakeClient({"Sunday Robotics": [{"title": "x", "url": "x", "snippet": "x"}]})
    count = enrich_all_companies(conn, client=client)
    assert count == 0


def test_enrich_all_processes_unenriched(conn):
    insert_discovered_company(
        conn,
        {
            "company_name": "Acme AI",
            "talent_count": 2,
            "talent_sources": "{}",
            "category": "unknown",
        },
    )
    client = FakeClient(
        {
            "Sunday Robotics": [
                {
                    "title": "Sunday Robotics humanoid robot",
                    "url": "https://sundayrobotics.com",
                    "snippet": "Robot company.",
                }
            ],
            "Acme AI": [
                {
                    "title": "Acme AI foundation model $100 million",
                    "url": "https://acme.ai",
                    "snippet": "LLM company. $100 million.",
                }
            ],
        }
    )
    count = enrich_all_companies(conn, client=client)
    assert count == 2
