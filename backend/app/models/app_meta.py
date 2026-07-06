from __future__ import annotations

from datetime import date as Date
from typing import Optional

from sqlmodel import Field, SQLModel


class AppMeta(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    last_news_fetch_date: Optional[Date] = None
