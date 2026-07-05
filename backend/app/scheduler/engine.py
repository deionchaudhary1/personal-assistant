"""Pure scheduling engine.

ZERO I/O. No FastAPI, no SQLModel, no DB imports. Everything is expressed with
small dataclasses and plain functions so the semantics can be tested without
any mocks.

Datetimes are naive local `datetime` objects. Dates are `date` objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date
from datetime import datetime, time, timedelta
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class SchedulableTask:
    """A task the engine is allowed to place."""

    id: int
    title: str
    priority: str  # "high" | "medium" | "low"
    estimated_minutes: int
    created_at: datetime
    due_date: Optional[Date] = None


@dataclass(frozen=True)
class Interval:
    """A half-open [start, end) time interval (naive local datetimes)."""

    start: datetime
    end: datetime


@dataclass(frozen=True)
class Slot:
    """A free interval available for placement."""

    start: datetime
    end: datetime

    @property
    def length_minutes(self) -> float:
        return (self.end - self.start).total_seconds() / 60.0


@dataclass(frozen=True)
class WorkingWindow:
    """Working hours for a single day."""

    enabled: bool
    start: time  # local wall-clock start, e.g. 09:00
    end: time  # local wall-clock end, e.g. 17:00


@dataclass(frozen=True)
class PlacedBlock:
    """The engine's decision to place a task in a concrete time window."""

    task_id: int
    task_title: str
    task_priority: str
    date: Date
    start_time: datetime
    end_time: datetime


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def order_tasks(tasks: List[SchedulableTask]) -> List[SchedulableTask]:
    """Sort by (priority rank, due_date with None last, created_at)."""

    def key(t: SchedulableTask):
        rank = PRIORITY_RANK.get(t.priority, 1)
        # None due dates sort after any real due date.
        due_missing = t.due_date is None
        due_val = t.due_date or Date.max
        return (rank, due_missing, due_val, t.created_at)

    return sorted(tasks, key=key)


# ---------------------------------------------------------------------------
# Interval merging
# ---------------------------------------------------------------------------


def merge_intervals(intervals: List[Interval]) -> List[Interval]:
    """Merge overlapping and touching intervals into a minimal sorted list."""
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda i: (i.start, i.end))
    merged: List[Interval] = [ordered[0]]
    for cur in ordered[1:]:
        last = merged[-1]
        # Touching (cur.start == last.end) counts as mergeable.
        if cur.start <= last.end:
            if cur.end > last.end:
                merged[-1] = Interval(last.start, cur.end)
        else:
            merged.append(cur)
    return merged


# ---------------------------------------------------------------------------
# Free slot computation
# ---------------------------------------------------------------------------


def compute_free_slots(
    day: Date,
    working_hours_day: Optional[WorkingWindow],
    busy_intervals: List[Interval],
    existing_block_intervals: List[Interval],
    not_before: Optional[datetime] = None,
) -> List[Slot]:
    """Working window minus merged (busy + existing) intervals.

    Returns a sorted list of free Slots. Disabled or missing working hours
    yields no slots. If `not_before` is given, slots ending at/before it are
    dropped and slots straddling it are clipped to start at it.
    """
    if working_hours_day is None or not working_hours_day.enabled:
        return []

    window_start = datetime.combine(day, working_hours_day.start)
    window_end = datetime.combine(day, working_hours_day.end)
    if window_end <= window_start:
        return []

    # Apply not_before clipping to the whole window up front.
    if not_before is not None and not_before > window_start:
        window_start = not_before
    if window_start >= window_end:
        return []

    blocked = merge_intervals(list(busy_intervals) + list(existing_block_intervals))

    slots: List[Slot] = []
    cursor = window_start
    for iv in blocked:
        # Clip blocked interval to the window.
        b_start = max(iv.start, window_start)
        b_end = min(iv.end, window_end)
        if b_end <= window_start or b_start >= window_end:
            continue  # entirely outside window
        if b_start > cursor:
            slots.append(Slot(cursor, b_start))
        cursor = max(cursor, b_end)
        if cursor >= window_end:
            break
    if cursor < window_end:
        slots.append(Slot(cursor, window_end))

    # Drop zero/negative length slots defensively.
    return [s for s in slots if s.end > s.start]


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------


def schedule_day(
    day: Date,
    tasks: List[SchedulableTask],
    free_slots: List[Slot],
) -> Tuple[List[PlacedBlock], List[SchedulableTask]]:
    """Greedy first-fit placement of ordered tasks into free slots.

    A task fits a slot if estimated_minutes <= slot length. It is placed at
    the slot start and the slot shrinks. Tasks that fit no remaining slot are
    returned in the unplaceable list (never silently dropped).
    """
    ordered = order_tasks(tasks)
    # Mutable working copy of slots as (start, end) pairs.
    slots: List[List[datetime]] = [[s.start, s.end] for s in free_slots]

    placed: List[PlacedBlock] = []
    unplaceable: List[SchedulableTask] = []

    for task in ordered:
        duration = timedelta(minutes=task.estimated_minutes)
        fitted = False
        for slot in slots:
            slot_start, slot_end = slot
            if slot_start + duration <= slot_end:
                block_end = slot_start + duration
                placed.append(
                    PlacedBlock(
                        task_id=task.id,
                        task_title=task.title,
                        task_priority=task.priority,
                        date=day,
                        start_time=slot_start,
                        end_time=block_end,
                    )
                )
                slot[0] = block_end  # shrink slot
                fitted = True
                break
        if not fitted:
            unplaceable.append(task)

    return placed, unplaceable


@dataclass
class DayPlan:
    day: Date
    placed: List[PlacedBlock] = field(default_factory=list)


def schedule_week(
    start_day: Date,
    tasks: List[SchedulableTask],
    free_slots_by_day: List[List[Slot]],
) -> Tuple[List[DayPlan], List[SchedulableTask]]:
    """Fold placement across up to 7 days.

    `free_slots_by_day[i]` are the free slots for day `start_day + i`. A day's
    unplaceable tasks become the candidate list for the next day. Final
    leftovers are returned as unplaceable.
    """
    day_plans: List[DayPlan] = []
    candidates = list(tasks)

    for i, free_slots in enumerate(free_slots_by_day):
        day = start_day + timedelta(days=i)
        placed, leftover = schedule_day(day, candidates, free_slots)
        day_plans.append(DayPlan(day=day, placed=placed))
        candidates = leftover

    return day_plans, candidates
