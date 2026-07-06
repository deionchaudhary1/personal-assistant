from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    priority: str = "medium"  # high | medium | low
    status: str = "pending"  # pending | completed
    due_date: Optional[Date] = None
    created_at: datetime = Field(default_factory=datetime.now)
    source: str = "manual"  # manual | llm_parsed
