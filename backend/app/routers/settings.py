"""Working-hours settings."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import WorkingHours
from app.scheduler import service

router = APIRouter(prefix="/settings", tags=["settings"])


class WorkingHoursDay(BaseModel):
    day_of_week: int
    start: str = "09:00"
    end: str = "17:00"
    enabled: bool = True


@router.get("/working-hours")
def get_working_hours(session: Session = Depends(get_session)):
    rows = session.exec(
        select(WorkingHours).order_by(WorkingHours.day_of_week)
    ).all()
    return [service.working_hours_to_dict(r) for r in rows]


@router.put("/working-hours")
def put_working_hours(
    body: List[WorkingHoursDay], session: Session = Depends(get_session)
):
    existing = {
        r.day_of_week: r
        for r in session.exec(select(WorkingHours)).all()
    }
    for item in body:
        row = existing.get(item.day_of_week)
        if row is None:
            row = WorkingHours(day_of_week=item.day_of_week)
        row.start = item.start
        row.end = item.end
        row.enabled = item.enabled
        session.add(row)
    session.commit()
    rows = session.exec(
        select(WorkingHours).order_by(WorkingHours.day_of_week)
    ).all()
    return [service.working_hours_to_dict(r) for r in rows]
