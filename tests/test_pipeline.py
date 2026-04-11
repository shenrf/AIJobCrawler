"""Tests for pipeline.py."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3
import pytest

from db import init_db
from pipeline import get_companies_for_crawling, mark_company_crawled, run_full_pipeline


def _ins(conn, name, count, careers_url="", website=""):
    conn.execute(
        """INSERT INTO company_discovery (company_name, talent_count, talent_sources,
           careers_url, website, enriched)
           VALUES (?, ?, ?, ?, ?, 1)""",
        (name, count, json.dumps({"OpenAI": count}), careers_url, website),
    )
    conn.commit()


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c
    c.close()


class StubCrawler:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def crawl_company(self, name: str, url: str) -> None:
        self.calls.append((name, url))


def test_get_companies_skips_no_url(conn):
    _ins(conn, "WithURL", 5, careers_url="https://a.co/jobs", website="https://a.co")
    _ins(conn, "NoURL", 3)
    out = get_companies_for_crawling(conn)
    assert len(out) == 1
    assert out[0]["company_name"] == "WithURL"


def test_mark_crawled_excludes_from_pipeline(conn):
    _ins(conn, "Acme", 5, careers_url="https://acme.co/jobs")
    mark_company_crawled(conn, "Acme")
    out = get_companies_for_crawling(conn)
    assert out == []


def test_run_full_pipeline(conn, tmp_path):
    _ins(conn, "Acme", 5, careers_url="https://acme.co/jobs", website="https://acme.co")
    _ins(conn, "Beta", 3, careers_url="https://beta.co/jobs", website="https://beta.co")
    stub = StubCrawler()
    result = run_full_pipeline(conn, job_crawler=stub, output_dir=tmp_path)
    assert result["crawled"] == 2
    assert len(stub.calls) == 2
    assert result["tracker"].exists()
    for p in result["charts"]:
        assert p.exists()
    # Both marked crawled
    rows = conn.execute("SELECT added_to_pipeline FROM company_discovery").fetchall()
    assert all(r["added_to_pipeline"] == 1 for r in rows)
