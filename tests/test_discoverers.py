"""Tests for pluggable discoverers with mocked HTTP."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from discoverers.base import CompanyRecord, upsert_company
from discoverers.yc import YCDiscoverer
from discoverers.huggingface import HuggingFaceDiscoverer
from discoverers.ai_news import AINewsDiscoverer
from discoverers.runner import run_discoverers, _normalize

from db import get_connection, init_db


# ── YC ────────────────────────────────────────────────────────────────────────

def test_yc_parses_hits_and_maps_category():
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "hits": [
            {
                "name": "Suno",
                "website": "https://suno.ai",
                "batch": "W22",
                "one_liner": "AI music",
                "long_description": "Generative AI for music",
                "industries": ["Generative AI", "Consumer"],
                "all_locations": "Cambridge, MA; Remote",
            },
            {
                "name": "RoboCo",
                "website": "https://robo.co",
                "batch": "S23",
                "one_liner": "Robots",
                "industries": ["Robotics"],
                "all_locations": "",
            },
        ]
    }
    with patch("discoverers.yc.requests.post", return_value=fake_resp):
        recs = YCDiscoverer().discover()
    names = [r.company_name for r in recs]
    assert "Suno" in names
    robo = next(r for r in recs if r.company_name == "RoboCo")
    assert robo.category == "robotics"
    suno = next(r for r in recs if r.company_name == "Suno")
    assert suno.founded == "W22"
    assert suno.hq_location == "Cambridge, MA"


def test_yc_respects_limit():
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "hits": [{"name": f"Co{i}", "industries": ["AI"]} for i in range(10)]
    }
    with patch("discoverers.yc.requests.post", return_value=fake_resp):
        recs = YCDiscoverer().discover(limit=3)
    assert len(recs) == 3


# ── HuggingFace ───────────────────────────────────────────────────────────────

def test_huggingface_filters_single_model_authors_and_blocklist():
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = [
        {"modelId": "stabilityai/sd-xl", "downloads": 100},
        {"modelId": "stabilityai/sd-3", "downloads": 200},
        {"modelId": "stabilityai/sdv2", "downloads": 50},
        {"modelId": "loneuser/finetune", "downloads": 10},  # single model → filtered
        {"modelId": "facebook/llama", "downloads": 999},    # blocklisted
        {"modelId": "facebook/opt", "downloads": 888},
        {"modelId": "bert-base-uncased", "downloads": 1},   # no slash → skipped
    ]
    with patch("discoverers.huggingface.requests.get", return_value=fake_resp):
        recs = HuggingFaceDiscoverer().discover()
    names = [r.company_name for r in recs]
    assert "stabilityai" in names
    assert "loneuser" not in names
    assert "facebook" not in names
    stab = next(r for r in recs if r.company_name == "stabilityai")
    assert stab.website == "https://huggingface.co/stabilityai"
    assert stab.category == "foundation-model"


# ── AI News ───────────────────────────────────────────────────────────────────

_RSS_XML = """<?xml version="1.0"?><rss><channel>
<item>
  <title>Acme AI raises $50M Series B to build robots</title>
  <link>https://tc.com/1</link>
  <description>Desc</description>
</item>
<item>
  <title>Mega Corp nabs $1.2 billion for AI chips</title>
  <link>https://tc.com/2</link>
  <description>Desc</description>
</item>
<item>
  <title>This post is not funding news</title>
  <link>https://tc.com/3</link>
  <description>Desc</description>
</item>
</channel></rss>"""


def test_ai_news_parses_funding_headlines():
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.content = _RSS_XML.encode("utf-8")
    with patch("discoverers.ai_news.requests.get", return_value=fake_resp):
        recs = AINewsDiscoverer().discover()
    by_name = {r.company_name: r for r in recs}
    assert "Acme AI" in by_name
    assert by_name["Acme AI"].funding == "$50M"
    assert "Mega Corp" in by_name
    assert by_name["Mega Corp"].funding == "$1.2B"
    assert len(recs) == 2  # third headline has no funding pattern


# ── Runner dedup ──────────────────────────────────────────────────────────────

class _FakeDiscoverer:
    def __init__(self, name, records):
        self.source_name = name
        self._records = records

    def discover(self, limit=None):
        return self._records


def test_runner_dedupes_and_merges_fields():
    conn = get_connection(":memory:")
    init_db(conn)

    d1 = _FakeDiscoverer("src_a", [
        CompanyRecord(company_name="Foo Inc", source="src_a", website="https://foo.com"),
    ])
    d2 = _FakeDiscoverer("src_b", [
        CompanyRecord(
            company_name="foo",  # normalizes to same key
            source="src_b",
            funding="$10M",
            talent_sources={"OpenAI": 2},
        ),
    ])

    stats = run_discoverers(conn, [d1, d2])
    assert stats["total_candidates"] == 2
    assert stats["unique_candidates"] == 1
    assert stats["inserted"] == 1

    row = conn.execute(
        "SELECT website, funding, talent_count, talent_sources FROM company_discovery"
    ).fetchone()
    assert row["website"] == "https://foo.com"
    assert row["funding"] == "$10M"
    assert row["talent_count"] == 2
    assert json.loads(row["talent_sources"]) == {"OpenAI": 2}


def test_normalize_strips_suffixes():
    assert _normalize("Foo Inc.") == "foo"
    assert _normalize("  Bar LLC  ") == "bar"
    assert _normalize("Baz Corp") == "baz"


def test_upsert_merges_without_clobbering():
    conn = get_connection(":memory:")
    init_db(conn)
    upsert_company(conn, CompanyRecord(
        company_name="X", source="a", website="https://x.com", category="ai-app",
    ))
    upsert_company(conn, CompanyRecord(
        company_name="X", source="b", funding="$5M", talent_sources={"DeepMind": 3},
    ))
    row = conn.execute("SELECT * FROM company_discovery WHERE company_name='X'").fetchone()
    assert row["website"] == "https://x.com"
    assert row["funding"] == "$5M"
    assert row["category"] == "ai-app"
    assert row["talent_count"] == 3
