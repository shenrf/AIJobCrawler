"""Base crawler class with rate limiting, session management, dedup, and JSONL output."""

import json
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urlparse

import requests
from pybloom_live import ScalableBloomFilter

from config import HEADERS, REQUEST_DELAY_SEC, REQUEST_TIMEOUT_SEC, MAX_RETRIES, DATA_DIR

logger = logging.getLogger(__name__)

SKIP_EXTENSIONS = frozenset({
    '.pdf', '.zip', '.gz', '.tar', '.jpg', '.jpeg', '.png', '.gif',
    '.svg', '.mp4', '.mp3', '.wav', '.doc', '.docx', '.xls', '.xlsx',
    '.ppt', '.pptx', '.exe', '.dmg', '.iso', '.bin', '.7z', '.rar',
})


class BaseCrawler:
    """Base crawler with rate limiting, session management, dedup, error handling, and JSONL output.

    Subclass and override `parse(url, response)` to implement specific crawling logic.
    """

    def __init__(self, output_file: str | None = None, delay: float = REQUEST_DELAY_SEC,
                 timeout: int = REQUEST_TIMEOUT_SEC, max_retries: int = MAX_RETRIES) -> None:
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.output_file = Path(output_file) if output_file else None

        self._session = requests.Session()
        self._session.headers.update(HEADERS)

        self._visited: ScalableBloomFilter = ScalableBloomFilter(
            initial_capacity=10000, error_rate=0.001
        )
        self._last_request_time: dict[str, float] = {}  # per-domain rate limiting

    # --- Session management ---

    @property
    def session(self) -> requests.Session:
        return self._session

    def close(self) -> None:
        """Close the underlying requests session."""
        self._session.close()

    def __enter__(self) -> "BaseCrawler":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # --- Rate limiting (per-domain) ---

    def _enforce_rate_limit(self, url: str) -> None:
        domain = urlparse(url).netloc
        now = time.time()
        last = self._last_request_time.get(domain, 0.0)
        wait = self.delay - (now - last)
        if wait > 0:
            time.sleep(wait)
        self._last_request_time[domain] = time.time()

    # --- Dedup ---

    def _is_seen(self, url: str) -> bool:
        return url in self._visited

    def _mark_seen(self, url: str) -> None:
        self._visited.add(url)

    # --- Fetching ---

    def fetch(self, url: str) -> requests.Response | None:
        """Fetch a URL with rate limiting, retries, and dedup. Returns Response or None."""
        clean_url = urldefrag(url).url
        if self._is_seen(clean_url):
            logger.debug("Already visited: %s", clean_url)
            return None

        self._mark_seen(clean_url)
        self._enforce_rate_limit(clean_url)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._session.get(clean_url, timeout=self.timeout)
                # Also mark the final URL after redirects
                final_url = urldefrag(response.url).url
                if final_url != clean_url:
                    self._mark_seen(final_url)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning("Attempt %d/%d failed for %s: %s", attempt, self.max_retries, clean_url, e)
                if attempt < self.max_retries:
                    time.sleep(self.delay * attempt)  # backoff
        return None

    # --- JSONL output ---

    def save_jsonl(self, record: dict[str, Any], output_file: Path | str | None = None) -> None:
        """Append a record to a JSONL file."""
        path = Path(output_file) if output_file else self.output_file
        if path is None:
            raise ValueError("No output file specified")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # --- URL helpers ---

    @staticmethod
    def should_skip_url(url: str) -> bool:
        """Return True if URL points to a binary/non-HTML resource."""
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in SKIP_EXTENSIONS)

    # --- Subclass interface ---

    def parse(self, url: str, response: requests.Response) -> list[dict[str, Any]]:
        """Parse a response and return extracted records. Override in subclasses.

        Returns a list of dicts to be saved as JSONL records.
        """
        raise NotImplementedError("Subclasses must implement parse()")

    def crawl_url(self, url: str) -> list[dict[str, Any]]:
        """Fetch and parse a single URL. Returns extracted records."""
        response = self.fetch(url)
        if response is None:
            return []
        records = self.parse(url, response)
        if self.output_file:
            for record in records:
                self.save_jsonl(record)
        return records

    def crawl_urls(self, urls: list[str]) -> list[dict[str, Any]]:
        """Crawl a list of URLs sequentially. Returns all extracted records."""
        all_records: list[dict[str, Any]] = []
        for url in urls:
            records = self.crawl_url(url)
            all_records.extend(records)
            logger.info("Crawled %s — %d records", url, len(records))
        return all_records
