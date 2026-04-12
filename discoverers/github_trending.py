"""GitHub trending AI/ML organizations discoverer.

Searches GitHub's public API for repositories tagged with AI/ML topics,
extracts the unique organizations behind them, and emits CompanyRecords.
No API key required (unauthenticated: 60 requests/hour).
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from .base import CompanyDiscoverer, CompanyRecord

logger = logging.getLogger(__name__)

_GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"

_AI_TOPICS = [
    "machine-learning",
    "deep-learning",
    "artificial-intelligence",
    "large-language-model",
    "llm",
    "generative-ai",
    "computer-vision",
    "nlp",
    "reinforcement-learning",
    "robotics",
    "ai-agents",
    "diffusion-model",
    "transformers",
    "mlops",
]

_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "AIJobCrawler/0.3",
}

_SKIP_ORGS = {
    "github", "google", "microsoft", "facebook", "meta", "amazon", "aws",
    "apple", "tensorflow", "pytorch", "huggingface", "nvidia",
}


class GitHubTrendingDiscoverer(CompanyDiscoverer):
    source_name = "github_trending"

    def __init__(self, topics: Optional[list[str]] = None, min_stars: int = 100) -> None:
        self.topics = topics or _AI_TOPICS
        self.min_stars = min_stars

    def _search_topic(self, topic: str, per_page: int = 100) -> list[dict]:
        params = {
            "q": f"topic:{topic} stars:>={self.min_stars}",
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
        }
        try:
            resp = requests.get(_GITHUB_SEARCH_URL, params=params, headers=_HEADERS, timeout=15)
            if resp.status_code == 403:
                logger.warning(f"GitHub rate limit hit on topic={topic}")
                return []
            if resp.status_code != 200:
                logger.error(f"GitHub search returned {resp.status_code} for topic={topic}")
                return []
            return resp.json().get("items", [])
        except requests.RequestException as e:
            logger.error(f"GitHub search failed for topic={topic}: {e}")
            return []

    def discover(self, limit: Optional[int] = None) -> list[CompanyRecord]:
        orgs: dict[str, dict] = {}
        for topic in self.topics:
            repos = self._search_topic(topic)
            for repo in repos:
                owner = repo.get("owner", {})
                if owner.get("type") != "Organization":
                    continue
                login = (owner.get("login") or "").lower()
                if login in _SKIP_ORGS or not login:
                    continue
                entry = orgs.setdefault(login, {
                    "name": login,
                    "html_url": owner.get("html_url", ""),
                    "stars_total": 0,
                    "repo_count": 0,
                    "top_repos": [],
                    "topics": set(),
                })
                entry["stars_total"] += repo.get("stargazers_count", 0)
                entry["repo_count"] += 1
                entry["topics"].add(topic)
                if len(entry["top_repos"]) < 5:
                    entry["top_repos"].append(repo.get("full_name", ""))
            time.sleep(2)

        ranked = sorted(orgs.values(), key=lambda o: (o["repo_count"], o["stars_total"]), reverse=True)

        records: list[CompanyRecord] = []
        for org in ranked:
            topics_l = list(org["topics"])
            category = "ai-app"
            if any(t in topics_l for t in ["mlops", "ml-platform"]):
                category = "ai-infra"
            elif "robotics" in topics_l:
                category = "robotics"
            elif any(t in topics_l for t in ["large-language-model", "llm", "diffusion-model", "transformers"]):
                category = "foundation-model"

            records.append(
                CompanyRecord(
                    company_name=org["name"],
                    source=self.source_name,
                    website=org["html_url"],
                    category=category,
                    description=(
                        f"{org['repo_count']} AI repos, "
                        f"{org['stars_total']:,} total stars"
                    ),
                    source_meta={
                        "top_repos": org["top_repos"],
                        "topics": topics_l,
                    },
                )
            )
            if limit and len(records) >= limit:
                break
        return records
