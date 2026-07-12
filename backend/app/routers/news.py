"""Daily AI-news digest + read-tracking endpoints.

GET /api/news bundles the digest with engagement state (streak/pet) — the
panel always needs both together, and both share the same lazy catch-up
timing. The POST read endpoints return the same combined shape so the
client can re-render from any of them.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.engagement import service as engagement_service
from app.models import NewsItem
from app.news.service import get_digest

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
async def news_digest(session: Session = Depends(get_session)):
    engagement = engagement_service.recompute(session)
    items = await get_digest(session)
    return {"items": items, "engagement": engagement_service.to_dict(engagement)}


@router.post("/read-all")
async def mark_all_news_read(session: Session = Depends(get_session)):
    ids = [row.id for row in session.exec(select(NewsItem)).all() if row.id is not None]
    engagement = engagement_service.mark_read(session, ids)
    items = await get_digest(session)
    return {"items": items, "engagement": engagement_service.to_dict(engagement)}


@router.post("/{item_id}/read")
async def mark_news_read(item_id: int, session: Session = Depends(get_session)):
    engagement = engagement_service.mark_read(session, [item_id])
    items = await get_digest(session)
    return {"items": items, "engagement": engagement_service.to_dict(engagement)}
