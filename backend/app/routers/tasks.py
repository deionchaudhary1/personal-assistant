"""Task CRUD plus LLM parse endpoint."""

from __future__ import annotations

from datetime import date as Date
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.llm import ollama_client
from app.models import Task
from app.ordering import order_tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])


def task_to_dict(task: Task) -> Dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat(),
        "source": task.source,
    }


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[Date] = None
    source: str = "manual"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[Date] = None
    source: Optional[str] = None


class ParseRequest(BaseModel):
    text: str


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
    tasks = order_tasks(tasks)
    return [task_to_dict(t) for t in tasks]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, session: Session = Depends(get_session)):
    task = Task(
        title=body.title,
        description=body.description,
        priority=body.priority,
        due_date=body.due_date,
        source=body.source,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task_to_dict(task)


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
    return task_to_dict(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    session.commit()


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------


@router.post("/parse")
async def parse_tasks(body: ParseRequest):
    drafts = await ollama_client.parse_tasks(body.text)
    return {"drafts": drafts}
