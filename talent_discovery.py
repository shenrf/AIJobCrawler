"""Drive Google searches for each source lab and persist talent moves."""
from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from config import SEARCH_QUERY_TEMPLATES, SOURCE_LABS
from db import insert_talent_move
from profile_parser import parse_search_result
from search_client import GoogleSearchClient

logger = logging.getLogger(__name__)


class TalentDiscovery:
    """Run LinkedIn profile searches and store discovered talent moves."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        client: Optional[GoogleSearchClient] = None,
    ) -> None:
        self.conn = conn
        self.client = client or GoogleSearchClient()
        self.stats = {"queries_run": 0, "profiles_found": 0, "profiles_stored": 0}

    def _is_self_reference(self, current_company: str, source_lab: str) -> bool:
        """Return True if the person is still at the source lab."""
        if not current_company:
            return False
        c = current_company.lower().strip()
        s = source_lab.lower().strip()
        return c == s or c in s or s in c

    def discover_lab(
        self, lab_name: str, queries: list[str], max_queries: Optional[int] = None
    ) -> int:
        """Run searches for a single lab and store matches. Returns count stored."""
        stored = 0
        search_terms: list[str] = []
        for q in queries:
            for template in SEARCH_QUERY_TEMPLATES:
                search_terms.append(template.format(query=q))
        if max_queries is not None:
            search_terms = search_terms[:max_queries]

        for term in search_terms:
            logger.info(f"[{lab_name}] query: {term}")
            results = self.client.search(term)
            self.stats["queries_run"] += 1
            for r in results:
                parsed = parse_search_result(r, lab_name)
                if not parsed:
                    continue
                self.stats["profiles_found"] += 1
                if self._is_self_reference(parsed["current_company"], lab_name):
                    continue
                if not parsed["current_company"]:
                    # No destination company — can't aggregate, skip.
                    continue
                parsed["source_query"] = term
                try:
                    insert_talent_move(self.conn, parsed)
                    stored += 1
                    self.stats["profiles_stored"] += 1
                except sqlite3.Error as e:
                    logger.warning(f"DB insert failed for {parsed['linkedin_url']}: {e}")
        return stored

    def discover_all(self, max_queries_per_lab: Optional[int] = None) -> dict:
        """Iterate over all SOURCE_LABS and discover talent moves."""
        for lab in SOURCE_LABS:
            name = lab["name"]  # type: ignore[assignment]
            queries = lab["queries"]  # type: ignore[assignment]
            if isinstance(queries, str):
                queries = [queries]
            self.discover_lab(name, queries, max_queries_per_lab)  # type: ignore[arg-type]
        return dict(self.stats)
