"""Hacker News source adapter via the free, keyless Algolia HN Search API.

No API key/account required. There's no article abstract for HN stories, so
the "summary" field is a short points/comments blurb instead of prose.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

import httpx

HN_API_URL = "https://hn.algolia.com/api/v1/search"
MAX_RESULTS = 5
TIMEOUT = 15.0


def _parse_created_at(value: str) -> datetime:
    if not value:
        return datetime.now()
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class HackerNewsSource:
    name = "hackernews"
    refresh_interval = timedelta(hours=3)

    async def fetch(self) -> List[Dict[str, Any]]:
        params = {"tags": "front_page"}
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(HN_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        items: List[Dict[str, Any]] = []
        for hit in data.get("hits", []):
            if len(items) >= MAX_RESULTS:
                break
            title = hit.get("title") or hit.get("story_title")
            url = hit.get("url") or hit.get("story_url")
            object_id = hit.get("objectID")
            if not url and object_id:
                url = f"https://news.ycombinator.com/item?id={object_id}"
            if not title or not url:
                continue
            points = hit.get("points") or 0
            num_comments = hit.get("num_comments") or 0
            published_date = _parse_created_at(hit.get("created_at")).date()
            items.append(
                {
                    "title": title,
                    "summary": f"{points} points, {num_comments} comments",
                    "url": url,
                    "published_date": published_date,
                }
            )
        return items
