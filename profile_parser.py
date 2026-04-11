"""Parse Google search results for LinkedIn profile metadata.

Given a search result {title, url, snippet} from GoogleSearchClient, extract:
person_name, linkedin_url, current_company, current_title, previous_lab, previous_title.

Returns None for non-profile URLs or unparseable titles.
"""
from __future__ import annotations

import re
from typing import Optional


_SUFFIX_RE = re.compile(r"\s*[|\-–]\s*linkedin.*$", re.IGNORECASE)
_SEP_AT_RE = re.compile(r"\s+(?:at|@)\s+", re.IGNORECASE)


def _strip_suffix(title: str) -> str:
    """Remove ' | LinkedIn', ' - LinkedIn', trailing punctuation."""
    return _SUFFIX_RE.sub("", title).strip(" -|·")


def _split_name_rest(title: str) -> tuple[str, str]:
    """Split 'Name - Rest' into (name, rest). Tolerates em-dash and hyphens."""
    # Normalize dashes, then split on first ' - '
    for sep in [" - ", " – ", " — "]:
        if sep in title:
            name, rest = title.split(sep, 1)
            return name.strip(), rest.strip()
    return title.strip(), ""


def _split_title_company(rest: str) -> tuple[str, str]:
    """Split 'Title at Company' or 'Title, Company' into (title, company)."""
    if not rest:
        return "", ""
    # Prefer " at " / " @ " split
    m = _SEP_AT_RE.search(rest)
    if m:
        return rest[: m.start()].strip(), rest[m.end():].strip()
    # Fall back to last comma
    if "," in rest:
        title_part, company = rest.rsplit(",", 1)
        return title_part.strip(), company.strip()
    # Whole thing is title, no company
    return rest.strip(), ""


def _extract_previous_from_snippet(snippet: str, source_lab: str) -> tuple[str, str]:
    """Try to pull (previous_lab, previous_title) hints from snippet.

    We pin previous_lab to source_lab since we searched for it. Previous_title
    is best-effort from snippet text near the lab name.
    """
    if not snippet:
        return source_lab, ""
    # Look for "X at <source_lab>" or "<source_lab> X" patterns for the title
    prev_title = ""
    # "Former/ex <title> at <lab>"
    m = re.search(
        rf"(?:former(?:ly)?|ex[\s\-]+|previously)\s+([A-Z][\w\s]+?)\s+at\s+{re.escape(source_lab)}",
        snippet,
        re.IGNORECASE,
    )
    if m:
        prev_title = m.group(1).strip()
    return source_lab, prev_title


def parse_search_result(result: dict, source_lab: str) -> Optional[dict]:
    """Parse a Google search result into a talent move record.

    Args:
        result: {title, url, snippet} from GoogleSearchClient.search()
        source_lab: The lab we queried for (becomes previous_lab).

    Returns:
        dict with keys person_name, linkedin_url, current_company, current_title,
        previous_lab, previous_title — or None if unparseable.
    """
    url = (result.get("url") or "").strip()
    title = (result.get("title") or "").strip()
    snippet = (result.get("snippet") or "").strip()

    # Must be a LinkedIn profile URL
    if "/in/" not in url:
        return None
    if not title:
        return None

    title_clean = _strip_suffix(title)
    person_name, rest = _split_name_rest(title_clean)
    if not person_name:
        return None

    current_title, current_company = _split_title_company(rest)

    previous_lab, previous_title = _extract_previous_from_snippet(snippet, source_lab)

    return {
        "person_name": person_name,
        "linkedin_url": url,
        "current_company": current_company,
        "current_title": current_title,
        "previous_lab": previous_lab,
        "previous_title": previous_title,
    }
