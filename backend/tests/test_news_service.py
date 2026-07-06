"""Tests for app/news/service.py's lazy catch-up digest logic.

Uses an in-memory sqlite session and a monkeypatched fetch_daily_digest so no
network access is required. Async coroutines are driven with asyncio.run
directly (pytest-asyncio isn't a project dependency) inside plain sync test
functions.
"""

from __future__ import annotations

import asyncio
from datetime import date

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import AppMeta, NewsItem
from app.news import service


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _seed_meta(session: Session, last_fetch) -> None:
    session.add(AppMeta(id=1, last_news_fetch_date=last_fetch))
    session.commit()


def _seed_item(session: Session, title: str, published: date) -> None:
    session.add(
        NewsItem(
            source="arxiv",
            title=title,
            summary="summary",
            url=f"http://arxiv.org/abs/{title}",
            published_date=published,
        )
    )
    session.commit()


def test_no_fetch_when_already_run_today(session, monkeypatch):
    today = date.today()
    _seed_meta(session, today)
    _seed_item(session, "cached-1", today)

    called = False

    async def _fake_fetch():
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(service, "fetch_daily_digest", _fake_fetch)

    items = asyncio.run(service.get_digest(session))

    assert called is False
    assert len(items) == 1
    assert items[0]["title"] == "cached-1"


def test_fetch_and_replace_when_day_advanced(session, monkeypatch):
    yesterday = date(2026, 7, 4)
    _seed_meta(session, yesterday)
    _seed_item(session, "stale-item", yesterday)

    fresh = [
        {
            "title": "fresh-1",
            "summary": "new summary",
            "url": "http://arxiv.org/abs/fresh-1",
            "published_date": date.today(),
        }
    ]

    async def _fake_fetch():
        return fresh

    monkeypatch.setattr(service, "fetch_daily_digest", _fake_fetch)

    items = asyncio.run(service.get_digest(session))

    assert len(items) == 1
    assert items[0]["title"] == "fresh-1"

    meta = session.get(AppMeta, 1)
    assert meta.last_news_fetch_date == date.today()

    remaining_titles = {row.title for row in session.exec(select(NewsItem)).all()}
    assert remaining_titles == {"fresh-1"}


def test_fetch_failure_serves_stale_cache_without_raising(session, monkeypatch):
    yesterday = date(2026, 7, 4)
    _seed_meta(session, yesterday)
    _seed_item(session, "stale-item", yesterday)

    async def _fake_fetch():
        raise RuntimeError("network down")

    monkeypatch.setattr(service, "fetch_daily_digest", _fake_fetch)

    items = asyncio.run(service.get_digest(session))

    assert len(items) == 1
    assert items[0]["title"] == "stale-item"

    meta = session.get(AppMeta, 1)
    assert meta.last_news_fetch_date == yesterday
