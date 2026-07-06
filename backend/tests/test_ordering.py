"""Tests for app/ordering.py.

Constructs Task rows directly (SQLModel models can be instantiated without a
DB) and checks the sort order: priority rank, then due_date (None last),
then created_at as a tiebreak.
"""

from __future__ import annotations

from datetime import date, datetime

from app.models import Task
from app.ordering import order_tasks


def _task(id, priority="medium", created=None, due=None):
    return Task(
        id=id,
        title=f"t{id}",
        priority=priority,
        created_at=created or datetime(2026, 7, 1, 9, 0),
        due_date=due,
    )


def test_order_by_priority():
    tasks = [_task(1, "low"), _task(2, "high"), _task(3, "medium")]
    ordered = order_tasks(tasks)
    assert [t.id for t in ordered] == [2, 3, 1]


def test_order_by_priority_unknown_ranks_as_medium():
    tasks = [_task(1, "low"), _task(2, "weird"), _task(3, "high")]
    ordered = order_tasks(tasks)
    assert [t.id for t in ordered] == [3, 2, 1]


def test_order_by_due_date_none_last():
    tasks = [
        _task(1, "high", due=None),
        _task(2, "high", due=date(2026, 7, 10)),
        _task(3, "high", due=date(2026, 7, 5)),
    ]
    ordered = order_tasks(tasks)
    # Earliest due first, None last, all same priority.
    assert [t.id for t in ordered] == [3, 2, 1]


def test_order_by_created_at_tiebreak():
    tasks = [
        _task(1, "medium", created=datetime(2026, 7, 2, 9, 0)),
        _task(2, "medium", created=datetime(2026, 7, 1, 9, 0)),
    ]
    ordered = order_tasks(tasks)
    assert [t.id for t in ordered] == [2, 1]


def test_order_empty():
    assert order_tasks([]) == []
