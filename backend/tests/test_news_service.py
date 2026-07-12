"""Tests for app/news/service.py's per-source lazy catch-up digest logic.

Uses an in-memory sqlite session and fake source adapters (SOURCES is
monkeypatched on the service module) so no network access is required.
Async coroutines are driven with asyncio.run directly (pytest-asyncio isn't
a project dependency) inside plain sync test functions.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import NewsItem, SourceState
from app.news import service


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


class FakeSource:
    def __init__(self, name, items=None, error=None, refresh_interval=timedelta(hours=24)):
        self.name = name
        self.refresh_interval = refresh_interval
        self.items = items or []
        self.error = error
        self.fetch_count = 0

    async def fetch(self):
        self.fetch_count += 1
        if self.error is not None:
            raise self.error
        return self.items


def _item(title, published):
    return {
        "title": title,
        "summary": "summary",
        "url": f"http://example.com/{title}",
        "published_date": published,
    }


def _seed_item(session, title, published, source="fake", read_at=None):
    session.add(
        NewsItem(
            source=source,
            title=title,
            summary="summary",
            url=f"http://example.com/{title}",
            published_date=published,
            read_at=read_at,
        )
    )
    session.commit()


def _seed_state(session, source, last_fetched_at):
    session.add(SourceState(source=source, last_fetched_at=last_fetched_at))
    session.commit()


def test_no_fetch_when_recently_fetched(session, monkeypatch):
    today = date.today()
    fake = FakeSource("fake", items=[_item("fresh", today)])
    monkeypatch.setattr(service, "SOURCES", [fake])
    _seed_state(session, "fake", datetime.now() - timedelta(hours=1))
    _seed_item(session, "cached-1", today)

    items = asyncio.run(service.get_digest(session))

    assert fake.fetch_count == 0
    assert len(items) == 1
    assert items[0]["title"] == "cached-1"


def test_fetch_and_replace_only_that_sources_rows(session, monkeypatch):
    today = date.today()
    fake = FakeSource("fake", items=[_item("fresh-1", today)])
    monkeypatch.setattr(service, "SOURCES", [fake])
    _seed_state(session, "fake", datetime.now() - timedelta(days=2))
    _seed_item(session, "stale-item", today, source="fake")
    _seed_item(session, "other-source-item", today, source="other")

    items = asyncio.run(service.get_digest(session))

    assert fake.fetch_count == 1
    titles = {i["title"] for i in items}
    # The stale row for "fake" is replaced; the other source's cache is untouched.
    assert titles == {"fresh-1", "other-source-item"}

    state = session.get(SourceState, "fake")
    assert state.last_fetched_at is not None
    assert (datetime.now() - state.last_fetched_at) < timedelta(minutes=1)


def test_fetch_when_no_state_row_exists(session, monkeypatch):
    fake = FakeSource("fake", items=[_item("first-ever", date.today())])
    monkeypatch.setattr(service, "SOURCES", [fake])

    items = asyncio.run(service.get_digest(session))

    assert fake.fetch_count == 1
    assert [i["title"] for i in items] == ["first-ever"]


def test_fetch_failure_serves_stale_cache_without_raising(session, monkeypatch):
    yesterday = date(2026, 7, 4)
    fake = FakeSource("fake", error=RuntimeError("network down"))
    monkeypatch.setattr(service, "SOURCES", [fake])
    stale_time = datetime.now() - timedelta(days=2)
    _seed_state(session, "fake", stale_time)
    _seed_item(session, "stale-item", yesterday)

    items = asyncio.run(service.get_digest(session))

    assert len(items) == 1
    assert items[0]["title"] == "stale-item"
    # last_fetched_at is not advanced on failure, so the next call retries.
    state = session.get(SourceState, "fake")
    assert state.last_fetched_at == stale_time


def test_one_source_failing_does_not_blank_the_others(session, monkeypatch):
    today = date.today()
    good = FakeSource("good", items=[_item("good-1", today)])
    bad = FakeSource("bad", error=RuntimeError("boom"))
    monkeypatch.setattr(service, "SOURCES", [good, bad])
    _seed_item(session, "bad-cached", today, source="bad")

    items = asyncio.run(service.get_digest(session))

    titles = {i["title"] for i in items}
    assert titles == {"good-1", "bad-cached"}


def test_aggregate_sorted_desc_and_capped_at_15(session, monkeypatch):
    monkeypatch.setattr(service, "SOURCES", [])
    for offset in range(20):
        _seed_item(session, f"item-{offset}", date(2026, 7, 1) + timedelta(days=offset))

    items = asyncio.run(service.get_digest(session))

    assert len(items) == 15
    dates = [i["published_date"] for i in items]
    assert dates == sorted(dates, reverse=True)
    assert items[0]["title"] == "item-19"


def test_item_dict_includes_id_source_and_read_at(session, monkeypatch):
    monkeypatch.setattr(service, "SOURCES", [])
    read_time = datetime(2026, 7, 10, 12, 0)
    _seed_item(session, "read-item", date.today(), source="arxiv", read_at=read_time)

    items = asyncio.run(service.get_digest(session))

    item = items[0]
    assert item["source"] == "arxiv"
    assert isinstance(item["id"], int)
    assert item["read_at"] == read_time.isoformat()

    rows = session.exec(select(NewsItem)).all()
    assert len(rows) == 1
