"""Google Custom Search API client for LinkedIn profile discovery."""
import os
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class GoogleSearchClient:
    """Thin wrapper around Google Custom Search JSON API (free tier: 100/day)."""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: Optional[str] = None, cx: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.cx = cx or os.environ.get("GOOGLE_CX", "")
        self.last_request_time: float = 0.0
        self.daily_count: int = 0

    def search(self, query: str, num: int = 10) -> list[dict]:
        """Run a search query. Returns list of {title, url, snippet} dicts."""
        if not self.api_key or not self.cx:
            logger.warning("Google API key or CX not set. Returning empty.")
            return []

        elapsed = time.time() - self.last_request_time
        if elapsed < 1.5:
            time.sleep(1.5 - elapsed)

        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(num, 10),
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            self.last_request_time = time.time()
            self.daily_count += 1

            if resp.status_code == 429:
                logger.warning("Rate limited by Google. Stopping.")
                return []
            if resp.status_code != 200:
                logger.error(f"Google search failed: {resp.status_code}")
                return []

            data = resp.json()
            items = data.get("items", [])
            return [
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                }
                for item in items
            ]
        except requests.RequestException as e:
            logger.error(f"Search request failed: {e}")
            return []
