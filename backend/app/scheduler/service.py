"""DB-bound scheduling service.

Bridges the SQLModel persistence layer and the pure `engine` module. This is
where DB rows are turned into engine dataclasses, the engine's decisions are
persisted, and the contract's JSON shapes are assembled. `engine.py` stays
pure; all I/O lives here.

Naive local datetimes everywhere.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional

from sqlmodel import Session, select

from app.models import BusyBlock, Task, TimeBlock, WorkingHours
from app.scheduler import engine

# Blocks whose time is "consumed" and must not be re-planned over.
KEPT_STATUSES = ("done", "active")
# Task statuses eligible to be (re)scheduled.
CANDIDATE_TASK_STATUSES = ("pending", "scheduled")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def round_up_5min(dt: datetime) -> datetime:
    """Round a datetime UP to the next 5-minute boundary."""
    discard = timedelta(
        minutes=dt.minute % 5,
        seconds=dt.second,
        microseconds=dt.microsecond,
    )
    dt = dt - discard
    if discard:
        dt = dt + timedelta(minutes=5)
    return dt


def day_bounds(day: Date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    return start, end


# ---------------------------------------------------------------------------
# DB -> engine adapters
# ---------------------------------------------------------------------------


def working_window_for(session: Session, day: Date) -> Optional[engine.WorkingWindow]:
    row = session.exec(
        select(WorkingHours).where(WorkingHours.day_of_week == day.weekday())
    ).first()
    if row is None:
        return None
    return engine.WorkingWindow(
        enabled=row.enabled,
        start=_parse_hhmm(row.start),
        end=_parse_hhmm(row.end),
    )


def _intervals_overlapping_day(
    rows_start_end: List[tuple[datetime, datetime]], day: Date
) -> List[engine.Interval]:
    d_start, d_end = day_bounds(day)
    out: List[engine.Interval] = []
    for start, end in rows_start_end:
        if end <= d_start or start >= d_end:
            continue
        out.append(engine.Interval(start=start, end=end))
    return out


def busy_intervals_for(session: Session, day: Date) -> List[engine.Interval]:
    d_start, d_end = day_bounds(day)
    rows = session.exec(
        select(BusyBlock).where(
            BusyBlock.start_time < d_end, BusyBlock.end_time > d_start
        )
    ).all()
    return _intervals_overlapping_day([(b.start_time, b.end_time) for b in rows], day)


def kept_block_intervals_for(session: Session, day: Date) -> List[engine.Interval]:
    rows = session.exec(
        select(TimeBlock).where(
            TimeBlock.date == day, TimeBlock.status.in_(KEPT_STATUSES)
        )
    ).all()
    return _intervals_overlapping_day([(b.start_time, b.end_time) for b in rows], day)


def to_schedulable(task: Task) -> engine.SchedulableTask:
    return engine.SchedulableTask(
        id=task.id,
        title=task.title,
        priority=task.priority,
        estimated_minutes=task.estimated_minutes,
        created_at=task.created_at,
        due_date=task.due_date,
    )


def free_slots_for(session: Session, day: Date, today: Date) -> List[engine.Slot]:
    window = working_window_for(session, day)
    busy = busy_intervals_for(session, day)
    existing = kept_block_intervals_for(session, day)
    not_before = None
    if day == today:
        not_before = round_up_5min(datetime.now())
    return engine.compute_free_slots(day, window, busy, existing, not_before=not_before)


# ---------------------------------------------------------------------------
# Serialization to contract JSON shapes
# ---------------------------------------------------------------------------


def task_to_dict(task: Task) -> Dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "estimated_minutes": task.estimated_minutes,
        "status": task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat(),
        "source": task.source,
    }


def block_to_dict(session: Session, block: TimeBlock) -> Dict:
    task = session.get(Task, block.task_id)
    return {
        "id": block.id,
        "task_id": block.task_id,
        "task_title": task.title if task else "(deleted)",
        "task_priority": task.priority if task else "medium",
        "date": block.date.isoformat(),
        "start_time": block.start_time.isoformat(),
        "end_time": block.end_time.isoformat(),
        "status": block.status,
    }


def busy_to_dict(block: BusyBlock) -> Dict:
    return {
        "id": block.id,
        "title": block.title,
        "start_time": block.start_time.isoformat(),
        "end_time": block.end_time.isoformat(),
        "source": block.source,
        "gcal_event_id": block.gcal_event_id,
    }


def working_hours_to_dict(row: WorkingHours) -> Dict:
    return {
        "day_of_week": row.day_of_week,
        "start": row.start,
        "end": row.end,
        "enabled": row.enabled,
    }


def working_hours_dict_for_day(session: Session, day: Date) -> Optional[Dict]:
    row = session.exec(
        select(WorkingHours).where(WorkingHours.day_of_week == day.weekday())
    ).first()
    return working_hours_to_dict(row) if row else None


def day_schedule(session: Session, day: Date) -> Dict:
    blocks = session.exec(
        select(TimeBlock)
        .where(TimeBlock.date == day)
        .order_by(TimeBlock.start_time)
    ).all()
    d_start, d_end = day_bounds(day)
    busy = session.exec(
        select(BusyBlock)
        .where(BusyBlock.start_time < d_end, BusyBlock.end_time > d_start)
        .order_by(BusyBlock.start_time)
    ).all()
    return {
        "date": day.isoformat(),
        "time_blocks": [block_to_dict(session, b) for b in blocks],
        "busy_blocks": [busy_to_dict(b) for b in busy],
        "working_hours": working_hours_dict_for_day(session, day),
    }


# ---------------------------------------------------------------------------
# Core: run scheduling and persist
# ---------------------------------------------------------------------------


def _candidate_tasks(session: Session, days: List[Date]) -> List[engine.SchedulableTask]:
    tasks = session.exec(
        select(Task).where(Task.status.in_(CANDIDATE_TASK_STATUSES))
    ).all()
    # Exclude tasks that still hold a live block: planned/active on ANY date
    # (in-range planned blocks were already deleted, so a remaining planned
    # block means the task is scheduled on a day outside this rerun range and
    # re-placing it would duplicate it), plus done blocks in-range.
    kept_task_ids = set(
        session.exec(
            select(TimeBlock.task_id).where(
                TimeBlock.status.in_(("planned", "active"))
            )
        ).all()
    )
    for day in days:
        rows = session.exec(
            select(TimeBlock.task_id).where(
                TimeBlock.date == day, TimeBlock.status == "done"
            )
        ).all()
        kept_task_ids.update(rows)
    return [to_schedulable(t) for t in tasks if t.id not in kept_task_ids]


def run_schedule(session: Session, scope: str, start_date: Optional[Date] = None) -> Dict:
    """Delete planned blocks in range, greedily (re)schedule candidate tasks.

    Returns a ScheduleRunResult dict. Does NOT resync notifications — the caller
    (router / rollover) owns the resync choke point.
    """
    today = datetime.now().date()
    if start_date is None:
        start_date = today

    num_days = 7 if scope == "week" else 1
    days = [start_date + timedelta(days=i) for i in range(num_days)]

    # Delete existing planned blocks in range (keep done/skipped/active).
    for day in days:
        planned = session.exec(
            select(TimeBlock).where(
                TimeBlock.date == day, TimeBlock.status == "planned"
            )
        ).all()
        for block in planned:
            session.delete(block)
    session.commit()

    candidates = _candidate_tasks(session, days)
    free_slots_by_day = [free_slots_for(session, day, today) for day in days]

    day_plans, unplaceable = engine.schedule_week(
        start_date, candidates, free_slots_by_day
    )

    placed_task_ids = set()
    for plan in day_plans:
        for pb in plan.placed:
            session.add(
                TimeBlock(
                    task_id=pb.task_id,
                    date=pb.date,
                    start_time=pb.start_time,
                    end_time=pb.end_time,
                    status="planned",
                )
            )
            placed_task_ids.add(pb.task_id)
    # Set placed tasks' status to scheduled.
    for task_id in placed_task_ids:
        task = session.get(Task, task_id)
        if task and task.status == "pending":
            task.status = "scheduled"
    session.commit()

    unplaceable_tasks = []
    for st in unplaceable:
        task = session.get(Task, st.id)
        if task:
            unplaceable_tasks.append(task_to_dict(task))

    return {
        "days": [day_schedule(session, day) for day in days],
        "unplaceable": unplaceable_tasks,
    }
