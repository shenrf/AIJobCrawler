"""HuggingFace discoverer.

Pulls the most-downloaded models from the HF API and collects their unique
authors/orgs as candidate AI companies. Catches anyone publishing open models
(Suno, Black Forest Labs, Nous Research, Mistral, Stability, etc.).
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

from .base import CompanyDiscoverer, CompanyRecord

logger = logging.getLogger(__name__)

_HF_MODELS_URL = "https://huggingface.co/api/models"

# Known-personal authors we want to skip (individual researchers, not orgs).
# HF doesn't cleanly distinguish. A reasonable filter: skip authors whose name
# matches common personal patterns. We err on the side of inclusion — duplicates
# and false positives are easier to remove later than missing companies.
_BLOCKLIST = {
    "bert-base-uncased", "gpt2", "t5-base", "t5-small", "t5-large",
    "distilbert-base-uncased", "facebook", "google", "microsoft",
}


class HuggingFaceDiscoverer(CompanyDiscoverer):
    source_name = "huggingface"

    def __init__(self, model_sample: int = 500) -> None:
        self.model_sample = model_sample

    def _fetch_models(self) -> list[dict]:
        params = {
            "sort": "downloads",
            "direction": -1,
            "limit": self.model_sample,
        }
        try:
            resp = requests.get(_HF_MODELS_URL, params=params, timeout=15)
            if resp.status_code != 200:
                logger.error(f"HF API returned {resp.status_code}")
                return []
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"HF API request failed: {e}")
            return []

    def discover(self, limit: Optional[int] = None) -> list[CompanyRecord]:
        models = self._fetch_models()
        seen: dict[str, dict] = {}
        for m in models:
            model_id = m.get("modelId") or m.get("id") or ""
            if "/" not in model_id:
                continue
            author = model_id.split("/", 1)[0]
            if author in _BLOCKLIST:
                continue
            entry = seen.setdefault(
                author,
                {"download_total": 0, "models": []},
            )
            entry["download_total"] += m.get("downloads", 0) or 0
            entry["models"].append(model_id)

        records: list[CompanyRecord] = []
        # Prefer authors with multiple models — single-model authors are
        # usually individuals fine-tuning.
        ranked = sorted(
            seen.items(),
            key=lambda kv: (len(kv[1]["models"]), kv[1]["download_total"]),
            reverse=True,
        )
        for author, meta in ranked:
            if len(meta["models"]) < 2:
                continue
            records.append(
                CompanyRecord(
                    company_name=author,
                    source=self.source_name,
                    website=f"https://huggingface.co/{author}",
                    category="foundation-model",
                    description=(
                        f"{len(meta['models'])} public HF models, "
                        f"{meta['download_total']:,} total downloads"
                    ),
                    source_meta={"top_models": meta["models"][:5]},
                )
            )
            if limit and len(records) >= limit:
                break
        return records
