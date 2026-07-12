from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SourceState(SQLModel, table=True):
    """One row per registered news source adapter, tracking its own fetch cadence."""

    source: str = Field(primary_key=True)
    last_fetched_at: Optional[datetime] = None
