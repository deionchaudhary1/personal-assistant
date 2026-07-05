"""End-of-day rollover logic.

Given the tasks the user actually completed today: mark them completed and
their blocks done; every other planned/active block today becomes skipped and
its task returns to pending; then re-run week scheduling starting tomorrow so
the unfinished work rolls forward by priority.

DB-bound; delegates placement to `service.run_schedule`. Does NOT resync
notifications — the caller owns that choke point.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlmodel import Session, select

from app.models import Task, TimeBlock
from app.scheduler import service


def end_of_day(
    session: Session,
    completed_task_ids: List[int],
    day: Optional[Date] = None,
) -> Dict:
    """Apply end-of-day review and reschedule the remainder.

    Returns a ScheduleRunResult dict for the week starting the next day.
    """
    if day is None:
        day = datetime.now().date()
    completed = set(completed_task_ids or [])

    blocks = session.exec(
        select(TimeBlock).where(TimeBlock.date == day)
    ).all()

    for block in blocks:
        if block.task_id in completed:
            # Completed task: its blocks are done.
            block.status = "done"
        elif block.status in ("planned", "active"):
            # Unfinished work: skip the block, task goes back to pending.
            block.status = "skipped"

    # Mark completed tasks completed.
    for task_id in completed:
        task = session.get(Task, task_id)
        if task:
            task.status = "completed"

    # Any task with a skipped block today (and not completed) returns to pending.
    for block in blocks:
        if block.status == "skipped" and block.task_id not in completed:
            task = session.get(Task, block.task_id)
            if task and task.status != "completed":
                task.status = "pending"

    session.commit()

    # Re-run week scheduling starting the next day.
    next_day = day + timedelta(days=1)
    return service.run_schedule(session, scope="week", start_date=next_day)
