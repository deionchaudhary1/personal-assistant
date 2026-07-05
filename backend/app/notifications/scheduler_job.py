"""APScheduler wiring and the notification resync choke point."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlmodel import Session, select

from app.db import engine
from app.models import TimeBlock, Task
from app.notifications.notifier import notify

_scheduler: Optional[BackgroundScheduler] = None

NOTIFY_PREFIX = "notify-start-"


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def start_scheduler() -> None:
    sched = get_scheduler()
    if not sched.running:
        sched.start()
    # 30-minute calendar poll.
    sched.add_job(
        _calendar_poll_job,
        trigger="interval",
        minutes=30,
        id="calendar-poll",
        replace_existing=True,
    )
    # 21:00 daily safety-net notification.
    sched.add_job(
        _safety_net_job,
        trigger=CronTrigger(hour=21, minute=0),
        id="safety-net",
        replace_existing=True,
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


def _notify_block(task_title: str, until: str) -> None:
    notify("Personal Assistant", f"Now: {task_title} (until {until})")


def _calendar_poll_job() -> None:
    """Poll Google Calendar every 30 min; no-op if not connected."""
    try:
        from app.calendar_sync import google_client

        if not google_client.is_connected():
            return
        with Session(engine) as session:
            google_client.sync_events(session)
        resync_notification_jobs(datetime.now().date())
    except Exception:
        pass


def _safety_net_job() -> None:
    """At 21:00, notify about unfinished blocks; never auto-roll."""
    try:
        today = datetime.now().date()
        with Session(engine) as session:
            blocks = session.exec(
                select(TimeBlock).where(TimeBlock.date == today)
            ).all()
            unfinished = [b for b in blocks if b.status in ("planned", "active")]
        if unfinished:
            notify(
                "Personal Assistant",
                f"You have {len(unfinished)} unfinished blocks — run End of Day Review",
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# The single resync choke point
# ---------------------------------------------------------------------------


def resync_notification_jobs(day: Date) -> None:
    """Remove all notify-start jobs and re-add one per future planned block today.

    Called after every mutation that can change today's blocks, and on startup.
    """
    sched = get_scheduler()
    # Remove existing notify-start jobs.
    for job in list(sched.get_jobs()):
        if job.id and job.id.startswith(NOTIFY_PREFIX):
            try:
                sched.remove_job(job.id)
            except Exception:
                pass

    now = datetime.now()
    try:
        with Session(engine) as session:
            blocks = session.exec(
                select(TimeBlock).where(
                    TimeBlock.date == day,
                    TimeBlock.status == "planned",
                )
            ).all()
            for block in blocks:
                if block.start_time <= now:
                    continue
                task = session.get(Task, block.task_id)
                title = task.title if task else "Task"
                until = block.end_time.strftime("%H:%M")
                sched.add_job(
                    _notify_block,
                    trigger=DateTrigger(run_date=block.start_time),
                    args=[title, until],
                    id=f"{NOTIFY_PREFIX}{block.id}",
                    replace_existing=True,
                )
    except Exception:
        pass
