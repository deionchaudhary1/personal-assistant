from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class WorkingHours(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_of_week: int = Field(index=True)  # 0=Monday .. 6=Sunday
    start: str = "09:00"  # HH:MM
    end: str = "17:00"  # HH:MM
    enabled: bool = True
