"""Pluggable company discoverers.

Each discoverer finds AI companies from a different source (YC directory,
HuggingFace orgs, AI news, LinkedIn talent flow) and emits a unified
CompanyRecord that gets upserted into the `company_discovery` table.
"""
from .base import CompanyDiscoverer, CompanyRecord, upsert_company

__all__ = ["CompanyDiscoverer", "CompanyRecord", "upsert_company"]
