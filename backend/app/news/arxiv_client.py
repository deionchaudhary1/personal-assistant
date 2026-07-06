"""arXiv Atom-feed client for the daily AI news digest.

Parsing is split out as pure functions (``parse_feed`` / ``_truncate_summary``)
so tests can exercise them against a hand-written XML fixture with no
network access. ``fetch_daily_digest`` does the HTTP call and raises on any
network/parse failure — the caller (``app.news.service``) decides the
fallback, matching the never-break-the-page posture of
``app.llm.ollama_client``.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date as Date
from datetime import datetime
from typing import Any, Dict, List

import httpx

ARXIV_API_URL = "https://export.arxiv.org/api/query"
SEARCH_QUERY = "cat:cs.AI OR cat:cs.LG OR cat:cs.CL"
MAX_RESULTS = 5
TIMEOUT = 15.0

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_SUMMARY_LIMIT = 200


def _truncate_summary(raw: str, limit: int = _SUMMARY_LIMIT) -> str:
    """Collapse arXiv's newline-wrapped abstract and truncate it.

    Uses the first sentence when it fits within ``limit`` chars; otherwise
    falls back to a hard truncation at ``limit`` chars with a trailing
    ellipsis — i.e. whichever of the two is shorter.
    """
    collapsed = " ".join(raw.split())
    sentence_match = re.search(r"(.*?[.!?])(\s|$)", collapsed)
    first_sentence = sentence_match.group(1).strip() if sentence_match else collapsed
    if len(first_sentence) <= limit:
        return first_sentence
    return collapsed[:limit].rstrip() + "…"


def _parse_published_date(value: str) -> Date:
    # arXiv publishes e.g. "2024-01-15T18:00:00Z".
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def parse_feed(xml_bytes: bytes) -> List[Dict[str, Any]]:
    """Parse an arXiv Atom feed into a list of digest-item dicts."""
    root = ET.fromstring(xml_bytes)
    items: List[Dict[str, Any]] = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        title_el = entry.find("atom:title", _ATOM_NS)
        summary_el = entry.find("atom:summary", _ATOM_NS)
        id_el = entry.find("atom:id", _ATOM_NS)
        published_el = entry.find("atom:published", _ATOM_NS)
        if title_el is None or summary_el is None or id_el is None or published_el is None:
            continue
        title = " ".join((title_el.text or "").split())
        url = (id_el.text or "").strip()
        items.append(
            {
                "title": title,
                "summary": _truncate_summary(summary_el.text or ""),
                "url": url,
                "published_date": _parse_published_date((published_el.text or "").strip()),
            }
        )
    return items


async def fetch_daily_digest() -> List[Dict[str, Any]]:
    """Query the arXiv API, parse the Atom feed, return up to 5 digest items.

    Raises on network/parse failure — caller decides the fallback.
    """
    params = {
        "search_query": SEARCH_QUERY,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": MAX_RESULTS,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(ARXIV_API_URL, params=params)
        resp.raise_for_status()
        body = resp.content
    return parse_feed(body)
