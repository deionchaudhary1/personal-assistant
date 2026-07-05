from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class OAuthToken(SQLModel, table=True):
    """Singleton row (id=1) holding Google OAuth credentials as JSON."""

    id: Optional[int] = Field(default=None, primary_key=True)
    creds_json: str  # JSON-serialized google.oauth2.credentials.Credentials
    last_synced_at: Optional[datetime] = None
