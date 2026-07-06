"""Lazy catch-up digest service.

Whenever the digest is requested: if AppMeta.last_news_fetch_date is today,
serve the cached NewsItem rows. Otherwise, try to fetch a fresh digest from
arXiv; on success replace the cached rows and advance the date; on failure
log a warning and serve whatever is cached (even if stale) — never raise to
the route, matching the never-break-the-UI posture used elsewhere in the app.
"""

from __future__ import annotations

import logging
from datetime import date as Date
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models import AppMeta, NewsItem
from app.news.arxiv_client import fetch_daily_digest

logger = logging.getLogger(__name__)


def _news_item_to_dict(item: NewsItem) -> Dict[str, Any]:
    return {
        "title": item.title,
        "summary": item.summary,
        "url": item.url,
        "published_date": item.published_date.isoformat(),
    }


def _get_or_create_meta(session: Session) -> AppMeta:
    meta = session.get(AppMeta, 1)
    if meta is None:
        meta = AppMeta(id=1, last_news_fetch_date=None)
        session.add(meta)
        session.commit()
        session.refresh(meta)
    return meta


def _cached_items(session: Session) -> List[Dict[str, Any]]:
    rows = session.exec(select(NewsItem)).all()
    return [_news_item_to_dict(r) for r in rows]


async def get_digest(session: Session) -> List[Dict[str, Any]]:
    meta = _get_or_create_meta(session)
    today = Date.today()

    if meta.last_news_fetch_date == today:
        return _cached_items(session)

    try:
        fresh = await fetch_daily_digest()
    except Exception:
        logger.warning("arXiv digest fetch failed; serving cached news items", exc_info=True)
        return _cached_items(session)

    existing = session.exec(select(NewsItem)).all()
    for row in existing:
        session.delete(row)

    now = datetime.now()
    for entry in fresh:
        session.add(
            NewsItem(
                source="arxiv",
                title=entry["title"],
                summary=entry["summary"],
                url=entry["url"],
                published_date=entry["published_date"],
                fetched_at=now,
            )
        )

    meta.last_news_fetch_date = today
    session.add(meta)
    session.commit()

    return _cached_items(session)
