from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class TimeBlock(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    date: Date = Field(index=True)
    start_time: datetime
    end_time: datetime
    status: str = "planned"  # planned | active | done | skipped
