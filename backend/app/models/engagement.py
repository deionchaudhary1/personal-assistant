from __future__ import annotations

from datetime import date as Date
from typing import Optional

from sqlmodel import Field, SQLModel


class Engagement(SQLModel, table=True):
    """Singleton row (id=1) tracking the read-everything streak and pet state."""

    id: int = Field(default=1, primary_key=True)
    current_streak: int = 0
    longest_streak: int = 0
    last_all_read_date: Optional[Date] = None
    pet_stage: int = 0
    pet_happiness: int = 100
    last_reminder_sent_date: Optional[Date] = None
