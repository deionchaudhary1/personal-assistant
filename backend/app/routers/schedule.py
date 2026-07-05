"""Schedule read + run + end-of-day + block PATCH endpoints."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.models import Task, TimeBlock
from app.notifications.scheduler_job import resync_notification_jobs
from app.scheduler import rollover, service

router = APIRouter(prefix="/schedule", tags=["schedule"])


class RunRequest(BaseModel):
    scope: str = "day"
    start_date: Optional[Date] = None


class EndOfDayRequest(BaseModel):
    date: Optional[Date] = None
    completed_task_ids: List[int] = []


class BlockUpdate(BaseModel):
    status: str


def _today() -> Date:
    return datetime.now().date()


@router.get("/day")
def get_day(date: Optional[Date] = None, session: Session = Depends(get_session)):
    day = date or _today()
    return service.day_schedule(session, day)


@router.get("/week")
def get_week(start: Optional[Date] = None, session: Session = Depends(get_session)):
    start_day = start or _today()
    days = [service.day_schedule(session, start_day + timedelta(days=i)) for i in range(7)]
    return {"days": days}


@router.post("/run")
def run(body: RunRequest, session: Session = Depends(get_session)):
    scope = body.scope if body.scope in ("day", "week") else "day"
    result = service.run_schedule(session, scope=scope, start_date=body.start_date)
    resync_notification_jobs(_today())
    return result


@router.post("/end-of-day")
def end_of_day(body: EndOfDayRequest, session: Session = Depends(get_session)):
    result = rollover.end_of_day(
        session, completed_task_ids=body.completed_task_ids, day=body.date
    )
    resync_notification_jobs(_today())
    return result


@router.patch("/blocks/{block_id}")
def update_block(
    block_id: int, body: BlockUpdate, session: Session = Depends(get_session)
):
    block = session.get(TimeBlock, block_id)
    if block is None:
        raise HTTPException(status_code=404, detail="Time block not found")
    block.status = body.status
    # Task status side-effects.
    task = session.get(Task, block.task_id)
    if task is not None:
        if body.status == "done":
            task.status = "completed"
        elif body.status == "skipped":
            task.status = "pending"
        elif body.status == "active":
            task.status = "in_progress"
    session.add(block)
    session.commit()
    session.refresh(block)
    resync_notification_jobs(_today())
    return service.block_to_dict(session, block)
