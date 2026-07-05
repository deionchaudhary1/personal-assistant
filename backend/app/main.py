"""FastAPI application entrypoint.

Wires routers under /api, CORS for the Vite dev server, DB + FTS5 + working-hours
seeding on startup, and the APScheduler background jobs (calendar poll, 21:00
safety net, per-block notifications).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.db import create_db_and_tables, engine
from app.documents.ingest import create_fts_table
from app.models import WorkingHours
from app.notifications.scheduler_job import (
    resync_notification_jobs,
    shutdown_scheduler,
    start_scheduler,
)
from app.routers import (
    busy_blocks,
    calendar,
    documents,
    health,
    schedule,
    settings,
    tasks,
)


def _seed_working_hours(session: Session) -> None:
    existing = session.exec(select(WorkingHours)).first()
    if existing is not None:
        return
    for dow in range(7):
        weekend = dow >= 5  # 5=Sat, 6=Sun
        session.add(
            WorkingHours(
                day_of_week=dow,
                start="09:00",
                end="17:00",
                enabled=not weekend,
            )
        )
    session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup.
    create_db_and_tables()
    with Session(engine) as session:
        create_fts_table(session)
        _seed_working_hours(session)
    start_scheduler()
    resync_notification_jobs(datetime.now().date())
    yield
    # Shutdown.
    shutdown_scheduler()


app = FastAPI(title="Personal Scheduling Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (
    health,
    tasks,
    schedule,
    busy_blocks,
    calendar,
    documents,
    settings,
):
    app.include_router(module.router, prefix="/api")
