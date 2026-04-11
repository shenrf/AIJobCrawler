"""Tests for profile_parser.parse_search_result."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from profile_parser import parse_search_result


def test_format_name_title_at_company():
    result = {
        "title": "Jane Doe - Research Scientist at Sunday Robotics | LinkedIn",
        "url": "https://linkedin.com/in/janedoe",
        "snippet": "Former Research Scientist at OpenAI. Now building robots.",
    }
    out = parse_search_result(result, "OpenAI")
    assert out is not None
    assert out["person_name"] == "Jane Doe"
    assert out["linkedin_url"] == "https://linkedin.com/in/janedoe"
    assert out["current_title"] == "Research Scientist"
    assert out["current_company"] == "Sunday Robotics"
    assert out["previous_lab"] == "OpenAI"
    assert out["previous_title"] == "Research Scientist"


def test_format_name_title_comma_company():
    result = {
        "title": "John Smith - Staff ML Engineer, Acme AI | LinkedIn",
        "url": "https://www.linkedin.com/in/jsmith/",
        "snippet": "ex-Anthropic. Scaling LLMs.",
    }
    out = parse_search_result(result, "Anthropic")
    assert out is not None
    assert out["person_name"] == "John Smith"
    assert out["current_title"] == "Staff ML Engineer"
    assert out["current_company"] == "Acme AI"
    assert out["previous_lab"] == "Anthropic"


def test_format_name_title_at_sign():
    result = {
        "title": "Alice Wong - Research Engineer @ Prometheus AI",
        "url": "https://linkedin.com/in/alicewong",
        "snippet": "Previously at Google DeepMind.",
    }
    out = parse_search_result(result, "Google DeepMind")
    assert out is not None
    assert out["person_name"] == "Alice Wong"
    assert out["current_company"] == "Prometheus AI"
    assert out["current_title"] == "Research Engineer"


def test_non_profile_url_returns_none():
    result = {
        "title": "Some company page | LinkedIn",
        "url": "https://linkedin.com/company/foo",
        "snippet": "whatever",
    }
    assert parse_search_result(result, "OpenAI") is None


def test_empty_title_returns_none():
    result = {"title": "", "url": "https://linkedin.com/in/foo", "snippet": ""}
    assert parse_search_result(result, "OpenAI") is None


def test_no_company_info():
    result = {
        "title": "Bob Lee - Software Engineer",
        "url": "https://linkedin.com/in/boblee",
        "snippet": "Ex-xAI.",
    }
    out = parse_search_result(result, "xAI")
    assert out is not None
    assert out["person_name"] == "Bob Lee"
    assert out["current_title"] == "Software Engineer"
    assert out["current_company"] == ""
    assert out["previous_lab"] == "xAI"


def test_em_dash_separator():
    result = {
        "title": "Carlos Ruiz — Research Scientist at Stealth Startup | LinkedIn",
        "url": "https://linkedin.com/in/cruiz",
        "snippet": "formerly at Meta FAIR",
    }
    out = parse_search_result(result, "Meta FAIR")
    assert out is not None
    assert out["person_name"] == "Carlos Ruiz"
    assert out["current_company"] == "Stealth Startup"
