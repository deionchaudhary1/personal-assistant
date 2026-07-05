"""Task CRUD plus LLM parse/estimate endpoints."""

from __future__ import annotations

from datetime import date as Date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.llm import ollama_client
from app.models import Task, TimeBlock
from app.notifications.scheduler_job import resync_notification_jobs
from app.scheduler import engine, service

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    estimated_minutes: int = 30
    due_date: Optional[Date] = None
    source: str = "manual"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    estimated_minutes: Optional[int] = None
    status: Optional[str] = None
    due_date: Optional[Date] = None
    source: Optional[str] = None


class ParseRequest(BaseModel):
    text: str


class EstimateRequest(BaseModel):
    title: str
    description: Optional[str] = ""


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("")
def list_tasks(
    status: Optional[str] = None,
    session: Session = Depends(get_session),
):
    stmt = select(Task)
    if status:
        stmt = stmt.where(Task.status == status)
    tasks = session.exec(stmt).all()
    # Sort by priority rank, then due_date (None last), then created_at.
    schedulable_order = {t.id: i for i, t in enumerate(
        engine.order_tasks([service.to_schedulable(t) for t in tasks])
    )}
    tasks.sort(key=lambda t: schedulable_order.get(t.id, 0))
    return [service.task_to_dict(t) for t in tasks]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, session: Session = Depends(get_session)):
    task = Task(
        title=body.title,
        description=body.description,
        priority=body.priority,
        estimated_minutes=body.estimated_minutes,
        due_date=body.due_date,
        source=body.source,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return service.task_to_dict(task)


@router.patch("/{task_id}")
def update_task(
    task_id: int, body: TaskUpdate, session: Session = Depends(get_session)
):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    data = body.model_dump(exclude_unset=True)
    for field_name, value in data.items():
        setattr(task, field_name, value)
    session.add(task)
    session.commit()
    session.refresh(task)
    return service.task_to_dict(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    blocks = session.exec(
        select(TimeBlock).where(TimeBlock.task_id == task_id)
    ).all()
    for block in blocks:
        session.delete(block)
    session.delete(task)
    session.commit()
    # Deleting a task can remove today's blocks -> resync notifications.
    resync_notification_jobs(_today())


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------


@router.post("/parse")
async def parse_tasks(body: ParseRequest):
    drafts = await ollama_client.parse_tasks(body.text)
    return {"drafts": drafts}


@router.post("/estimate")
async def estimate_task(body: EstimateRequest):
    minutes = await ollama_client.estimate_minutes(body.title, body.description or "")
    return {"estimated_minutes": minutes}


def _today() -> Date:
    from datetime import datetime

    return datetime.now().date()
