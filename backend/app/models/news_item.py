from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class NewsItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = "arxiv"
    title: str
    summary: str
    url: str
    published_date: Date
    fetched_at: datetime = Field(default_factory=datetime.now)
