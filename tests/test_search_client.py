import pytest
import requests
from unittest.mock import patch, MagicMock
from search_client import GoogleSearchClient


def test_search_returns_parsed_results():
    mock_response = {
        "items": [
            {
                "title": "John Doe - Staff ML Engineer at CoolStartup | LinkedIn",
                "link": "https://www.linkedin.com/in/johndoe/",
                "snippet": "Previously: Research Scientist at OpenAI. Now building next-gen AI at CoolStartup."
            }
        ]
    }
    with patch("search_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        client = GoogleSearchClient(api_key="test", cx="test")
        results = client.search("site:linkedin.com/in ex-OpenAI")
        assert len(results) == 1
        assert results[0]["title"] == "John Doe - Staff ML Engineer at CoolStartup | LinkedIn"
        assert results[0]["url"] == "https://www.linkedin.com/in/johndoe/"
        assert "OpenAI" in results[0]["snippet"]


def test_search_handles_empty_response():
    with patch("search_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {})
        client = GoogleSearchClient(api_key="test", cx="test")
        results = client.search("site:linkedin.com/in ex-OpenAI")
        assert results == []


def test_search_handles_rate_limit():
    with patch("search_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=429)
        client = GoogleSearchClient(api_key="test", cx="test")
        results = client.search("site:linkedin.com/in ex-OpenAI")
        assert results == []


def test_search_handles_request_exception():
    with patch("search_client.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("Connection error")
        client = GoogleSearchClient(api_key="test", cx="test")
        results = client.search("site:linkedin.com/in ex-OpenAI")
        assert results == []


def test_search_returns_empty_without_credentials():
    client = GoogleSearchClient(api_key="", cx="")
    results = client.search("test query")
    assert results == []
