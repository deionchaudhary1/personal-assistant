from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class BusyBlock(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    start_time: datetime = Field(index=True)
    end_time: datetime
    source: str = "manual"  # manual | gcal
    gcal_event_id: Optional[str] = None
