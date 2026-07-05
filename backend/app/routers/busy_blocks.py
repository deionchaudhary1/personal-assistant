"""Manual + gcal-mirrored busy blocks."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import BusyBlock
from app.notifications.scheduler_job import resync_notification_jobs
from app.scheduler import service

router = APIRouter(prefix="/busy-blocks", tags=["busy-blocks"])


class BusyCreate(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime


def _today() -> Date:
    return datetime.now().date()


@router.get("")
def list_busy(date: Optional[Date] = None, session: Session = Depends(get_session)):
    stmt = select(BusyBlock)
    if date is not None:
        start, end = service.day_bounds(date)
        stmt = stmt.where(BusyBlock.start_time < end, BusyBlock.end_time > start)
    rows = session.exec(stmt.order_by(BusyBlock.start_time)).all()
    return [service.busy_to_dict(b) for b in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_busy(body: BusyCreate, session: Session = Depends(get_session)):
    block = BusyBlock(
        title=body.title,
        start_time=body.start_time,
        end_time=body.end_time,
        source="manual",
    )
    session.add(block)
    session.commit()
    session.refresh(block)
    resync_notification_jobs(_today())
    return service.busy_to_dict(block)


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_busy(block_id: int, session: Session = Depends(get_session)):
    block = session.get(BusyBlock, block_id)
    if block is None:
        raise HTTPException(status_code=404, detail="Busy block not found")
    if block.source != "manual":
        raise HTTPException(
            status_code=400, detail="Cannot delete a calendar-sourced busy block"
        )
    session.delete(block)
    session.commit()
    resync_notification_jobs(_today())
