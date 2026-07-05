"""Google Calendar OAuth + sync.

Degrades gracefully: if backend/credentials.json is missing or tokens are
absent, calendar features raise CalendarUnavailable (translated to 503 by the
router). The server must always start without credentials.json.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import List, Optional

from sqlmodel import Session, select

from app.db import BACKEND_DIR
from app.models import BusyBlock, OAuthToken

CREDENTIALS_PATH = os.path.join(BACKEND_DIR, "credentials.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
REDIRECT_URI = "http://localhost:8000/api/calendar/oauth-callback"


class CalendarUnavailable(Exception):
    """Raised when calendar features cannot proceed (missing creds/tokens)."""


def credentials_configured() -> bool:
    return os.path.exists(CREDENTIALS_PATH)


def _get_token_row(session: Session) -> Optional[OAuthToken]:
    return session.get(OAuthToken, 1)


def is_connected() -> bool:
    """True if we have stored OAuth tokens (does not verify remote validity)."""
    if not credentials_configured():
        return False
    try:
        from app.db import engine

        with Session(engine) as session:
            return _get_token_row(session) is not None
    except Exception:
        return False


def last_synced_at() -> Optional[datetime]:
    try:
        from app.db import engine

        with Session(engine) as session:
            row = _get_token_row(session)
            return row.last_synced_at if row else None
    except Exception:
        return None


def _require_credentials() -> None:
    if not credentials_configured():
        raise CalendarUnavailable(
            "Google credentials.json is not present in the backend directory. "
            "Add it to enable calendar features."
        )


def build_auth_url() -> str:
    _require_credentials()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(
        CREDENTIALS_PATH, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return auth_url


def exchange_code(session: Session, code: str) -> None:
    _require_credentials()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(
        CREDENTIALS_PATH, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    _store_credentials(session, creds)


def _store_credentials(session: Session, creds) -> None:
    creds_json = creds.to_json()
    row = _get_token_row(session)
    if row is None:
        row = OAuthToken(id=1, creds_json=creds_json)
        session.add(row)
    else:
        row.creds_json = creds_json
    session.commit()


def _load_credentials(session: Session):
    _require_credentials()
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    row = _get_token_row(session)
    if row is None:
        raise CalendarUnavailable(
            "Google Calendar is not connected. Visit the auth URL to connect."
        )
    info = json.loads(row.creds_json)
    creds = Credentials.from_authorized_user_info(info, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _store_credentials(session, creds)
    return creds


def sync_events(session: Session) -> int:
    """Pull [today, today+14d] primary-calendar events, replacing gcal blocks."""
    creds = _load_credentials(session)
    from googleapiclient.discovery import build

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    now = datetime.now()
    start = datetime.combine(now.date(), datetime.min.time())
    end = start + timedelta(days=14)

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start.astimezone().isoformat(),
            timeMax=end.astimezone().isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    # Replace existing gcal busy blocks.
    existing = session.exec(
        select(BusyBlock).where(BusyBlock.source == "gcal")
    ).all()
    for b in existing:
        session.delete(b)
    session.commit()

    count = 0
    for event in events:
        start_info = event.get("start", {})
        end_info = event.get("end", {})
        # Skip all-day events (they use 'date' not 'dateTime').
        if "dateTime" not in start_info or "dateTime" not in end_info:
            continue
        start_dt = _parse_naive(start_info["dateTime"])
        end_dt = _parse_naive(end_info["dateTime"])
        block = BusyBlock(
            title=event.get("summary", "(busy)"),
            start_time=start_dt,
            end_time=end_dt,
            source="gcal",
            gcal_event_id=event.get("id"),
        )
        session.add(block)
        count += 1

    row = _get_token_row(session)
    if row is not None:
        row.last_synced_at = datetime.now()
    session.commit()
    return count


def _parse_naive(dt_str: str) -> datetime:
    """Parse an RFC3339 datetime string into a naive local datetime."""
    # Normalize trailing Z to +00:00 for fromisoformat.
    normalized = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt
