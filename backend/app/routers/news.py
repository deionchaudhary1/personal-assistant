"""Daily AI-news digest endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.news.service import get_digest

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
async def news_digest(session: Session = Depends(get_session)):
    items = await get_digest(session)
    return {"items": items}
