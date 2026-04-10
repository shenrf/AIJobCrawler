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
