"""Multi-source, per-adapter lazy catch-up digest service.

For each registered source (app.news.registry.SOURCES): if that source's
SourceState.last_fetched_at is missing or older than the adapter's own
refresh_interval, try to fetch fresh items. On success, replace only that
source's cached NewsItem rows and advance its SourceState. On failure, log a
warning and keep serving that source's existing cached rows — one source
failing never blanks out the others, and never raises to the route (matching
the never-break-the-UI posture used elsewhere in the app).

After the per-source refresh pass, all cached NewsItem rows (across every
source) are aggregated, sorted by published_date descending, and capped at a
digest-sized total.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models import NewsItem, SourceState
from app.news.registry import SOURCES
from app.news.sources.base import SourceAdapter

logger = logging.getLogger(__name__)

DIGEST_CAP = 15


def _news_item_to_dict(item: NewsItem) -> Dict[str, Any]:
    return {
        "id": item.id,
        "source": item.source,
        "title": item.title,
        "summary": item.summary,
        "url": item.url,
        "published_date": item.published_date.isoformat(),
        "read_at": item.read_at.isoformat() if item.read_at else None,
    }


def _get_or_create_source_state(session: Session, source: str) -> SourceState:
    state = session.get(SourceState, source)
    if state is None:
        state = SourceState(source=source, last_fetched_at=None)
        session.add(state)
        session.commit()
        session.refresh(state)
    return state


async def _refresh_source(session: Session, adapter: SourceAdapter) -> None:
    state = _get_or_create_source_state(session, adapter.name)
    now = datetime.now()

    is_stale = state.last_fetched_at is None or (now - state.last_fetched_at) >= adapter.refresh_interval
    if not is_stale:
        return

    try:
        fresh = await adapter.fetch()
    except Exception:
        logger.warning(
            "%s digest fetch failed; serving cached news items", adapter.name, exc_info=True
        )
        return

    existing = session.exec(select(NewsItem).where(NewsItem.source == adapter.name)).all()
    for row in existing:
        session.delete(row)

    for entry in fresh:
        session.add(
            NewsItem(
                source=adapter.name,
                title=entry["title"],
                summary=entry["summary"],
                url=entry["url"],
                published_date=entry["published_date"],
                fetched_at=now,
            )
        )

    state.last_fetched_at = now
    session.add(state)
    session.commit()


def _cached_items(session: Session) -> List[Dict[str, Any]]:
    rows = session.exec(select(NewsItem)).all()
    rows = sorted(rows, key=lambda r: r.published_date, reverse=True)
    return [_news_item_to_dict(r) for r in rows[:DIGEST_CAP]]


async def get_digest(session: Session) -> List[Dict[str, Any]]:
    for adapter in SOURCES:
        await _refresh_source(session, adapter)
    return _cached_items(session)
