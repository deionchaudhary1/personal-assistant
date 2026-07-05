"""Google Calendar OAuth + sync endpoints. Degrade to 503 without credentials."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.calendar_sync import google_client
from app.calendar_sync.google_client import CalendarUnavailable
from app.db import get_session
from app.notifications.scheduler_job import resync_notification_jobs

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _today() -> Date:
    return datetime.now().date()


@router.get("/status")
def status():
    return {
        "configured": google_client.credentials_configured(),
        "connected": google_client.is_connected(),
        "last_synced_at": (
            google_client.last_synced_at().isoformat()
            if google_client.last_synced_at()
            else None
        ),
    }


@router.get("/auth-url")
def auth_url():
    try:
        return {"url": google_client.build_auth_url()}
    except CalendarUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/oauth-callback")
def oauth_callback(code: str, state: str = "", session: Session = Depends(get_session)):
    try:
        google_client.exchange_code(session, code)
    except CalendarUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {exc}")
    return HTMLResponse(
        "<html><body><p>Connected — you can close this tab.</p></body></html>"
    )


@router.post("/sync")
def sync(session: Session = Depends(get_session)):
    try:
        count = google_client.sync_events(session)
    except CalendarUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    resync_notification_jobs(_today())
    return {"synced": count}
