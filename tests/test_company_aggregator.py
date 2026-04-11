"""Tests for company_aggregator.aggregate_companies."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3
import pytest

from db import init_db, insert_talent_move
from company_aggregator import aggregate_companies


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c
    c.close()


def _move(conn, name, url, prev_lab, company):
    insert_talent_move(
        conn,
        {
            "person_name": name,
            "linkedin_url": url,
            "previous_lab": prev_lab,
            "previous_title": "",
            "current_company": company,
            "current_title": "",
            "source_query": "",
        },
    )


def test_min_talent_threshold(conn):
    _move(conn, "A", "https://linkedin.com/in/a", "OpenAI", "Sunday Robotics")
    _move(conn, "B", "https://linkedin.com/in/b", "Anthropic", "Sunday Robotics")
    _move(conn, "C", "https://linkedin.com/in/c", "OpenAI", "Solo Startup")  # only 1 → excluded

    result = aggregate_companies(conn, min_talent=2)
    names = [r["company_name"] for r in result]
    assert "Sunday Robotics" in names
    assert "Solo Startup" not in names


def test_source_breakdown(conn):
    _move(conn, "A", "https://linkedin.com/in/a", "OpenAI", "Stealth AI")
    _move(conn, "B", "https://linkedin.com/in/b", "OpenAI", "Stealth AI")
    _move(conn, "C", "https://linkedin.com/in/c", "Anthropic", "Stealth AI")

    result = aggregate_companies(conn, min_talent=2)
    assert len(result) == 1
    row = result[0]
    assert row["company_name"] == "Stealth AI"
    assert row["talent_count"] == 3
    assert row["talent_sources"] == {"OpenAI": 2, "Anthropic": 1}


def test_writes_to_db(conn):
    _move(conn, "A", "https://linkedin.com/in/a", "OpenAI", "Acme")
    _move(conn, "B", "https://linkedin.com/in/b", "Anthropic", "Acme")

    aggregate_companies(conn, min_talent=2)
    rows = conn.execute("SELECT * FROM company_discovery").fetchall()
    assert len(rows) == 1
    assert rows[0]["company_name"] == "Acme"
    assert rows[0]["talent_count"] == 2
    sources = json.loads(rows[0]["talent_sources"])
    assert sources == {"OpenAI": 1, "Anthropic": 1}


def test_empty_company_excluded(conn):
    _move(conn, "A", "https://linkedin.com/in/a", "OpenAI", "")
    _move(conn, "B", "https://linkedin.com/in/b", "OpenAI", "")
    result = aggregate_companies(conn, min_talent=1)
    assert result == []


def test_reaggregate_updates_existing(conn):
    _move(conn, "A", "https://linkedin.com/in/a", "OpenAI", "Acme")
    _move(conn, "B", "https://linkedin.com/in/b", "OpenAI", "Acme")
    aggregate_companies(conn, min_talent=2)
    _move(conn, "C", "https://linkedin.com/in/c", "Anthropic", "Acme")
    aggregate_companies(conn, min_talent=2)
    rows = conn.execute("SELECT * FROM company_discovery WHERE company_name='Acme'").fetchall()
    assert len(rows) == 1
    assert rows[0]["talent_count"] == 3
