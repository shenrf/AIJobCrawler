"""Tests for tracker.generate_tracker_md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import sqlite3
import pytest

from db import init_db
from tracker import generate_tracker_md


def _ins(conn, name, count, sources, category="", funding="", hq="", website=""):
    conn.execute(
        """INSERT INTO company_discovery (company_name, talent_count, talent_sources,
           category, funding, hq_location, website, enriched)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
        (name, count, json.dumps(sources), category, funding, hq, website),
    )
    conn.commit()


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c
    c.close()


def test_rank_order(conn):
    _ins(conn, "Big Co", 10, {"OpenAI": 10}, "robotics", "$50M", "SF", "https://big.co")
    _ins(conn, "Mid Co", 5, {"Anthropic": 5}, "ai-infra", "$10M", "NYC", "https://mid.co")
    _ins(conn, "Small Co", 2, {"OpenAI": 2}, "ai-app", "$1M", "Austin", "https://small.co")

    md = generate_tracker_md(conn)
    assert "Big Co" in md
    assert "Mid Co" in md
    assert "Small Co" in md
    # Big Co appears before Mid Co
    assert md.index("Big Co") < md.index("Mid Co") < md.index("Small Co")


def test_stealth_section(conn):
    _ins(conn, "Known Co", 5, {"OpenAI": 5}, "ai-infra", "$5M", "SF", "https://known.co")
    _ins(conn, "Stealth Co", 3, {"Anthropic": 3})  # no website, no funding

    md = generate_tracker_md(conn)
    assert "## Stealth / Unverified" in md
    assert "Stealth Co" in md
    # Stealth Co should be in stealth section, not main table
    main_part, stealth_part = md.split("## Stealth / Unverified")
    assert "Stealth Co" not in main_part
    assert "Stealth Co" in stealth_part


def test_sources_formatted(conn):
    _ins(conn, "Multi Source", 5, {"OpenAI": 3, "Anthropic": 2}, "ai-infra", "$5M", "SF", "https://multi.co")
    md = generate_tracker_md(conn)
    assert "OpenAI (3)" in md
    assert "Anthropic (2)" in md


def test_write_to_file(conn, tmp_path):
    _ins(conn, "Acme", 2, {"OpenAI": 2}, "ai-app", "", "", "https://acme.co")
    out = tmp_path / "tracker.md"
    md = generate_tracker_md(conn, output_path=out)
    assert out.exists()
    assert out.read_text(encoding="utf-8") == md
    assert "Acme" in out.read_text(encoding="utf-8")


def test_empty_db(conn):
    md = generate_tracker_md(conn)
    assert "# AI Talent Flow Tracker" in md
