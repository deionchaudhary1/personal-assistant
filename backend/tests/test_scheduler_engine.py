"""Tests for the pure scheduling engine (app/scheduler/engine.py).

These exercise the engine's real, exposed API only — no DB, no FastAPI.
"""

from __future__ import annotations

from datetime import date, datetime, time

from app.scheduler import engine
from app.scheduler.engine import (
    Interval,
    SchedulableTask,
    Slot,
    WorkingWindow,
)

DAY = date(2026, 7, 6)  # a Monday


def _task(id, priority="medium", minutes=30, created=None, due=None):
    return SchedulableTask(
        id=id,
        title=f"t{id}",
        priority=priority,
        estimated_minutes=minutes,
        created_at=created or datetime(2026, 7, 1, 9, 0),
        due_date=due,
    )


def _dt(h, m=0):
    return datetime.combine(DAY, time(h, m))


# ---------------------------------------------------------------------------
# order_tasks
# ---------------------------------------------------------------------------


def test_order_by_priority():
    tasks = [_task(1, "low"), _task(2, "high"), _task(3, "medium")]
    ordered = engine.order_tasks(tasks)
    assert [t.id for t in ordered] == [2, 3, 1]


def test_order_by_due_date_none_last():
    tasks = [
        _task(1, "high", due=None),
        _task(2, "high", due=date(2026, 7, 10)),
        _task(3, "high", due=date(2026, 7, 5)),
    ]
    ordered = engine.order_tasks(tasks)
    # Earliest due first, None last, all same priority.
    assert [t.id for t in ordered] == [3, 2, 1]


def test_order_by_created_at_tiebreak():
    tasks = [
        _task(1, "medium", created=datetime(2026, 7, 2, 9, 0)),
        _task(2, "medium", created=datetime(2026, 7, 1, 9, 0)),
    ]
    ordered = engine.order_tasks(tasks)
    assert [t.id for t in ordered] == [2, 1]


def test_order_empty():
    assert engine.order_tasks([]) == []


# ---------------------------------------------------------------------------
# merge_intervals
# ---------------------------------------------------------------------------


def test_merge_overlapping():
    merged = engine.merge_intervals(
        [Interval(_dt(9), _dt(10)), Interval(_dt(9, 30), _dt(11))]
    )
    assert merged == [Interval(_dt(9), _dt(11))]


def test_merge_touching():
    merged = engine.merge_intervals(
        [Interval(_dt(9), _dt(10)), Interval(_dt(10), _dt(11))]
    )
    assert merged == [Interval(_dt(9), _dt(11))]


def test_merge_contained():
    merged = engine.merge_intervals(
        [Interval(_dt(9), _dt(12)), Interval(_dt(10), _dt(11))]
    )
    assert merged == [Interval(_dt(9), _dt(12))]


def test_merge_disjoint_and_empty():
    assert engine.merge_intervals([]) == []
    merged = engine.merge_intervals(
        [Interval(_dt(11), _dt(12)), Interval(_dt(9), _dt(10))]
    )
    assert merged == [Interval(_dt(9), _dt(10)), Interval(_dt(11), _dt(12))]


# ---------------------------------------------------------------------------
# compute_free_slots
# ---------------------------------------------------------------------------

WINDOW = WorkingWindow(enabled=True, start=time(9, 0), end=time(17, 0))


def test_free_slots_no_busy():
    slots = engine.compute_free_slots(DAY, WINDOW, [], [])
    assert slots == [Slot(_dt(9), _dt(17))]


def test_free_slots_subtracts_busy_and_existing():
    slots = engine.compute_free_slots(
        DAY,
        WINDOW,
        [Interval(_dt(10), _dt(11))],
        [Interval(_dt(13), _dt(14))],
    )
    assert slots == [
        Slot(_dt(9), _dt(10)),
        Slot(_dt(11), _dt(13)),
        Slot(_dt(14), _dt(17)),
    ]


def test_free_slots_disabled_day():
    disabled = WorkingWindow(enabled=False, start=time(9, 0), end=time(17, 0))
    assert engine.compute_free_slots(DAY, disabled, [], []) == []
    assert engine.compute_free_slots(DAY, None, [], []) == []


def test_free_slots_not_before_clips():
    slots = engine.compute_free_slots(DAY, WINDOW, [], [], not_before=_dt(11, 0))
    assert slots == [Slot(_dt(11), _dt(17))]


def test_free_slots_not_before_before_window_is_noop():
    slots = engine.compute_free_slots(DAY, WINDOW, [], [], not_before=_dt(7, 0))
    assert slots == [Slot(_dt(9), _dt(17))]


# ---------------------------------------------------------------------------
# schedule_day
# ---------------------------------------------------------------------------


def test_schedule_day_first_fit_placement():
    tasks = [_task(1, "high", 60), _task(2, "medium", 30)]
    slots = [Slot(_dt(9), _dt(17))]
    placed, unplaceable = engine.schedule_day(DAY, tasks, slots)
    assert unplaceable == []
    assert [(p.task_id, p.start_time, p.end_time) for p in placed] == [
        (1, _dt(9), _dt(10)),
        (2, _dt(10), _dt(10, 30)),
    ]


def test_schedule_day_unplaceable_when_nothing_fits():
    tasks = [_task(1, "high", 120)]
    slots = [Slot(_dt(9), _dt(10))]  # only 60 min free
    placed, unplaceable = engine.schedule_day(DAY, tasks, slots)
    assert placed == []
    assert [t.id for t in unplaceable] == [1]


def test_schedule_day_fills_across_slots():
    tasks = [_task(1, "high", 60), _task(2, "high", 60)]
    slots = [Slot(_dt(9), _dt(10)), Slot(_dt(14), _dt(15))]
    placed, unplaceable = engine.schedule_day(DAY, tasks, slots)
    assert unplaceable == []
    assert placed[0].start_time == _dt(9)
    assert placed[1].start_time == _dt(14)


def test_schedule_day_empty_inputs():
    assert engine.schedule_day(DAY, [], []) == ([], [])
    placed, unplaceable = engine.schedule_day(DAY, [_task(1)], [])
    assert placed == []
    assert [t.id for t in unplaceable] == [1]


# ---------------------------------------------------------------------------
# schedule_week
# ---------------------------------------------------------------------------


def test_schedule_week_spillover_to_next_day():
    # Two 60-min tasks, day 1 only has 60 min free -> second spills to day 2.
    tasks = [_task(1, "high", 60), _task(2, "high", 60)]
    day1_slots = [Slot(_dt(9), _dt(10))]
    day2_slots = [Slot(_dt(9), _dt(11))]
    day_plans, leftover = engine.schedule_week(DAY, tasks, [day1_slots, day2_slots])
    assert leftover == []
    assert [p.task_id for p in day_plans[0].placed] == [1]
    assert [p.task_id for p in day_plans[1].placed] == [2]
    assert day_plans[1].placed[0].date == date(2026, 7, 7)


def test_schedule_week_final_leftover_unplaceable():
    tasks = [_task(1, "high", 120), _task(2, "high", 120)]
    slots = [[Slot(_dt(9), _dt(10))], [Slot(_dt(9), _dt(10))]]
    day_plans, leftover = engine.schedule_week(DAY, tasks, slots)
    assert all(dp.placed == [] for dp in day_plans)
    assert {t.id for t in leftover} == {1, 2}


def test_schedule_week_empty():
    day_plans, leftover = engine.schedule_week(DAY, [], [[], []])
    assert leftover == []
    assert all(dp.placed == [] for dp in day_plans)
