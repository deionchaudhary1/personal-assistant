"""Read-streak and pet state logic.

recompute() is lazy catch-up, called at the top of GET /api/news (same
pattern as TASK-CARE.md's maintenance check): if a full day was skipped
since the last all-read day, the streak resets and the pet's happiness
takes a dent — no scheduler required, correctness is independent of when
the backend happens to run.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models import Engagement, NewsItem

HAPPINESS_PENALTY = 20
PET_MAX_STAGE = 4
STREAK_DAYS_PER_STAGE = 3


def _get_or_create(session: Session) -> Engagement:
    row = session.get(Engagement, 1)
    if row is None:
        row = Engagement(id=1)
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def recompute(session: Session) -> Engagement:
    """Lazy catch-up: if a day was fully skipped, reset the streak and dent happiness."""
    row = _get_or_create(session)
    today = Date.today()
    if row.last_all_read_date is not None and (today - row.last_all_read_date).days > 1:
        row.current_streak = 0
        row.pet_happiness = max(0, row.pet_happiness - HAPPINESS_PENALTY)
        # Clear the date so repeated recomputes don't re-apply the penalty.
        row.last_all_read_date = None
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def mark_read(session: Session, item_ids: List[int]) -> Engagement:
    """Mark the given NewsItem rows read; extend the streak if everything is read."""
    row = recompute(session)

    now = datetime.now()
    if item_ids:
        items = session.exec(select(NewsItem).where(NewsItem.id.in_(item_ids))).all()  # type: ignore[attr-defined]
        for item in items:
            if item.read_at is None:
                item.read_at = now
                session.add(item)
        session.commit()

    all_items = session.exec(select(NewsItem)).all()
    all_read = bool(all_items) and all(item.read_at is not None for item in all_items)

    today = Date.today()
    if all_read and row.last_all_read_date != today:
        yesterday = today - timedelta(days=1)
        if row.last_all_read_date == yesterday:
            row.current_streak += 1
        else:
            row.current_streak = 1
        row.longest_streak = max(row.longest_streak, row.current_streak)
        row.pet_stage = min(PET_MAX_STAGE, row.current_streak // STREAK_DAYS_PER_STAGE)
        row.last_all_read_date = today
        session.add(row)
        session.commit()
        session.refresh(row)

    return row


def to_dict(engagement: Engagement) -> Dict[str, Any]:
    return {
        "current_streak": engagement.current_streak,
        "longest_streak": engagement.longest_streak,
        "pet_stage": engagement.pet_stage,
        "pet_happiness": engagement.pet_happiness,
    }
