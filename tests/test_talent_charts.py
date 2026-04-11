"""Smoke tests for talent_charts — verify files are created."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3
import pytest

from db import init_db
from talent_charts import generate_sankey, generate_company_ranking_bar, generate_talent_heatmap


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    for name, count, sources in [
        ("Sunday Robotics", 8, {"OpenAI": 5, "Anthropic": 3}),
        ("Project Prometheus", 6, {"Amazon AGI": 6}),
        ("Stealth AI", 4, {"OpenAI": 2, "Google DeepMind": 2}),
        ("Acme", 3, {"Anthropic": 3}),
    ]:
        c.execute(
            """INSERT INTO company_discovery (company_name, talent_count, talent_sources)
               VALUES (?, ?, ?)""",
            (name, count, json.dumps(sources)),
        )
    c.commit()
    yield c
    c.close()


def test_sankey_creates_html(conn, tmp_path):
    out = tmp_path / "sankey.html"
    result = generate_sankey(conn, out)
    assert result.exists()
    assert out.stat().st_size > 0


def test_ranking_bar_creates_png(conn, tmp_path):
    out = tmp_path / "ranking.png"
    result = generate_company_ranking_bar(conn, out)
    assert result.exists()
    assert out.stat().st_size > 0


def test_heatmap_creates_png(conn, tmp_path):
    out = tmp_path / "heatmap.png"
    result = generate_talent_heatmap(conn, out)
    assert result.exists()
    assert out.stat().st_size > 0
