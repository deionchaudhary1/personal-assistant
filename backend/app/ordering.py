"""Task ordering.

Every render, tasks sort by priority (high -> medium -> low), then due date
(soonest first, no-due-date last), then creation time as a tiebreak. This
operates directly on `Task` rows.
"""

from __future__ import annotations

from datetime import date as Date
from typing import List

from app.models import Task

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def order_tasks(tasks: List[Task]) -> List[Task]:
    """Sort by (priority rank, due_date with None last, created_at)."""

    def key(t: Task):
        rank = PRIORITY_RANK.get(t.priority, 1)
        # None due dates sort after any real due date.
        due_missing = t.due_date is None
        due_val = t.due_date or Date.max
        return (rank, due_missing, due_val, t.created_at)

    return sorted(tasks, key=key)
