"""Generic RSS/Atom source adapter over a small hardcoded list of feed URLs.

Judgment call: the plan's example ("OpenAI, Anthropic, Google AI blogs") names
specific AI-lab blogs, but their exact current RSS URLs aren't something we
can verify without network access in this environment, and several labs have
moved/removed feeds over the years (OpenAI's blog RSS in particular has
changed paths multiple times). Rather than guess a lab-blog URL that may
already be dead, this picks three general-audience tech/AI feeds whose URL
patterns are long-stable and well-documented: MIT Technology Review's AI
topic feed, The Verge's AI topic feed, and Ars Technica's AI tag feed. Any
one of these silently 404ing does not break the digest — each feed fetch is
individually wrapped in try/except, matching the never-break-the-page
posture used by the other adapters.
"""

from __future__ import annotations

import asyncio
import html
import logging
import re
from datetime import date as Date
from datetime import datetime, timedelta
from time import mktime
from typing import Any, Dict, List, Optional

import feedparser

from app.news.sources.arxiv import _truncate_summary

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(raw: str) -> str:
    """RSS summaries often embed HTML; reduce to plain text before truncating."""
    return html.unescape(_TAG_RE.sub(" ", raw))

FEED_URLS = [
    "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://arstechnica.com/tag/ai/feed/",
]
MAX_RESULTS = 5
TIMEOUT = 15.0


def _entry_published_date(entry: Any) -> Optional[Date]:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(mktime(value)).date()
    return None


def _parse_entries(feed_url: str, parsed: Any) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for entry in parsed.entries:
        title = (entry.get("title") or "").strip()
        url = entry.get("link") or ""
        summary_raw = entry.get("summary") or entry.get("description") or ""
        published_date = _entry_published_date(entry)
        if not title or not url or published_date is None:
            continue
        items.append(
            {
                "title": title,
                "summary": _truncate_summary(_strip_html(summary_raw)) if summary_raw else "",
                "url": url,
                "published_date": published_date,
            }
        )
    return items


class RssSource:
    name = "blogs"
    refresh_interval = timedelta(hours=6)

    async def fetch(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for feed_url in FEED_URLS:
            try:
                # feedparser.parse is blocking network I/O; run off the event loop.
                parsed = await asyncio.to_thread(feedparser.parse, feed_url)
                if not parsed.entries and parsed.bozo:
                    raise ValueError(getattr(parsed, "bozo_exception", "feed parse failed"))
            except Exception:
                logger.warning("RSS feed fetch failed for %s", feed_url, exc_info=True)
                continue
            items.extend(_parse_entries(feed_url, parsed))

        items.sort(key=lambda i: i["published_date"], reverse=True)
        return items[:MAX_RESULTS]
