"""Web Push subscription endpoints.

The VAPID public key is served from the environment; it is an empty string
until keys are provisioned (key generation is handled outside this code —
the endpoints must not crash without it).
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import PushSubscription

router = APIRouter(prefix="/push", tags=["push"])


class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class SubscribeBody(BaseModel):
    endpoint: str
    keys: SubscriptionKeys


class UnsubscribeBody(BaseModel):
    endpoint: str


@router.get("/public-key")
def public_key():
    return {"public_key": os.environ.get("VAPID_PUBLIC_KEY", "")}


@router.post("/subscribe")
def subscribe(body: SubscribeBody, session: Session = Depends(get_session)):
    existing: Optional[PushSubscription] = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    ).first()
    if existing is not None:
        existing.p256dh = body.keys.p256dh
        existing.auth = body.keys.auth
        session.add(existing)
    else:
        session.add(
            PushSubscription(endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth)
        )
    session.commit()
    return {"ok": True}


@router.post("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(body: UnsubscribeBody, session: Session = Depends(get_session)):
    existing = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    ).first()
    if existing is not None:
        session.delete(existing)
        session.commit()
    # Idempotent: 204 whether or not the subscription existed.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
