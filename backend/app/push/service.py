"""Web Push reminder logic.

send_reminder_if_needed() is called by the background loop in app.main every
~30 minutes. It is a strict no-op until VAPID keys are provisioned in the
environment (VAPID_PRIVATE_KEY unset -> return immediately) so the loop can
run safely before key generation happens.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date as Date
from datetime import datetime

from sqlmodel import Session, select

from app.engagement import service as engagement_service
from app.models import NewsItem, PushSubscription

logger = logging.getLogger(__name__)

REMINDER_HOUR = 18  # Local hour after which the daily reminder may fire.


async def send_reminder_if_needed(session: Session) -> None:
    private_key = os.environ.get("VAPID_PRIVATE_KEY")
    if not private_key:
        # Keys not provisioned yet — must not crash the background loop.
        return

    # Import here so the app imports cleanly even if pywebpush is missing.
    from pywebpush import WebPushException, webpush

    subject = os.environ.get("VAPID_SUBJECT", "mailto:admin@example.com")

    engagement = engagement_service.recompute(session)
    today = Date.today()

    if engagement.last_reminder_sent_date == today:
        return
    if datetime.now().hour < REMINDER_HOUR:
        return

    unread = session.exec(select(NewsItem).where(NewsItem.read_at == None)).all()  # noqa: E711
    if not unread:
        return

    payload = json.dumps(
        {
            "title": "Today's digest is waiting",
            "body": f"{len(unread)} unread item{'s' if len(unread) != 1 else ''} — keep the streak going.",
        }
    )

    subscriptions = session.exec(select(PushSubscription)).all()
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": subject},
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                # Subscription expired/gone — self-cleaning delete.
                session.delete(sub)
                session.commit()
            else:
                logger.warning("Web push to %s failed", sub.endpoint, exc_info=True)
        except Exception:
            logger.warning("Web push to %s failed", sub.endpoint, exc_info=True)

    engagement.last_reminder_sent_date = today
    session.add(engagement)
    session.commit()
