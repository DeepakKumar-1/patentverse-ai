"""
Patent search tool.

Exposes a single plain-Python function, `search_patents`, that ADK agents
(and the MCP server) can use as a tool. It tries a real prior-art API first
(PatentsView) if a PATENTSVIEW_API_KEY is configured, and transparently
falls back to a bundled offline mock dataset otherwise — so the whole
project runs with zero external keys for demo/testing purposes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from tools.security import sanitize_search_query

load_dotenv()

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_patents.json"
_PATENTSVIEW_URL = "https://search.patentsview.org/api/v1/patent/"


def _load_mock_patents() -> list[dict[str, Any]]:
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_year(date_str: str) -> int | None:
    """Extract a 4-digit year from a YYYY-MM-DD style date string."""
    try:
        return int(date_str[:4])
    except (TypeError, ValueError, IndexError):
        return None


def _in_date_range(patent_date: str, date_from: str | None, date_to: str | None) -> bool:
    """Return True if patent_date falls within [date_from, date_to] (inclusive).

    date_from/date_to may be a year ("2015") or a full date ("2015-01-01").
    Patents with an unparsable date are excluded when a filter is active,
    since we can't verify they belong in the range.
    """
    if not date_from and not date_to:
        return True

    year = _parse_year(patent_date)
    if year is None:
        return False

    if date_from:
        from_year = _parse_year(date_from)
        if from_year is not None and year < from_year:
            return False
    if date_to:
        to_year = _parse_year(date_to)
        if to_year is not None and year > to_year:
            return False
    return True


def _search_mock(
    query: str, limit: int, date_from: str | None, date_to: str | None
) -> list[dict[str, Any]]:
    """Naive keyword-overlap search over the local mock dataset, with
    optional date-range filtering applied before ranking.

    Good enough for demo purposes; not meant to be a real ranking algorithm.
    """
    query_terms = {w for w in query.lower().split() if len(w) > 2}
    scored = []
    for patent in _load_mock_patents():
        if not _in_date_range(patent.get("date", ""), date_from, date_to):
            continue
        haystack = f"{patent['title']} {patent['abstract']}".lower()
        score = sum(1 for term in query_terms if term in haystack)
        if score > 0:
            scored.append((score, patent))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [p for _, p in scored[:limit]]


def _search_patentsview(
    query: str,
    limit: int,
    api_key: str,
    date_from: str | None,
    date_to: str | None,
) -> list[dict[str, Any]] | None:
    """Query the real PatentsView API. Returns None on any failure so the
    caller can fall back to mock data instead of crashing the agent run."""
    try:
        clauses: list[dict[str, Any]] = [{"_text_any": {"patent_title": query}}]
        if date_from:
            clauses.append({"_gte": {"patent_date": date_from}})
        if date_to:
            clauses.append({"_lte": {"patent_date": date_to}})

        payload = {
            "q": {"_and": clauses} if len(clauses) > 1 else clauses[0],
            "f": ["patent_id", "patent_title", "patent_date", "patent_abstract"],
            "o": {"size": limit},
        }
        resp = requests.post(
            _PATENTSVIEW_URL,
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("patents", [])[:limit]:
            results.append(
                {
                    "patent_id": item.get("patent_id", "unknown"),
                    "title": item.get("patent_title", ""),
                    "assignee": "N/A (PatentsView)",
                    "date": item.get("patent_date", ""),
                    "abstract": item.get("patent_abstract", ""),
                }
            )
        return results
    except (requests.RequestException, ValueError, KeyError):
        # Network error, bad response shape, etc. — fail soft to mock data.
        return None


def search_patents(
    query: str,
    limit: int = 5,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Search for patents related to a query string, optionally restricted
    to a date range.

    Args:
        query: A short description or keywords describing the invention
            or technology area to search for prior art against.
        limit: Maximum number of candidate patents to return (default 5).
        date_from: Optional earliest date to include, as "YYYY" or
            "YYYY-MM-DD" (e.g. "2015" or "2015-01-01"). Patents published
            before this are excluded.
        date_to: Optional latest date to include, same format as
            date_from. Patents published after this are excluded.

    Returns:
        A dict with keys:
            - "source": "patentsview" or "mock"
            - "results": list of patent records (patent_id, title, assignee,
              date, abstract) — every record includes its publication date.
    """
    query = sanitize_search_query(query)
    limit = max(1, min(int(limit), 20))
    date_from = date_from.strip() if date_from else None
    date_to = date_to.strip() if date_to else None

    api_key = os.getenv("PATENTSVIEW_API_KEY", "").strip()
    if api_key:
        real_results = _search_patentsview(query, limit, api_key, date_from, date_to)
        if real_results is not None:
            return {"source": "patentsview", "results": real_results}

    return {
        "source": "mock",
        "results": _search_mock(query, limit, date_from, date_to),
    }
