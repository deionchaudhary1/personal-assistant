"""FastAPI application entrypoint.

Wires routers under /api, CORS for the Vite dev server, creates DB tables on
startup, and serves the built frontend (frontend/dist) at / so the app runs
as a single process. Also owns the one scheduled primitive in the app: an
asyncio background loop that periodically checks whether a push reminder
should be sent (see plans/ENGAGE.md Approach §2 for why this exception to
the lazy-catch-up rule exists).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.db import create_db_and_tables, engine
from app.push.service import send_reminder_if_needed
from app.routers import health, news, push, tasks

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

REMINDER_TICK_SECONDS = 1800  # 30 minutes.

logger = logging.getLogger(__name__)


async def _reminder_loop() -> None:
    while True:
        await asyncio.sleep(REMINDER_TICK_SECONDS)
        try:
            with Session(engine) as session:
                await send_reminder_if_needed(session)
        except Exception:
            # One failed tick must not kill the loop.
            logger.warning("push reminder tick failed", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup.
    create_db_and_tables()
    reminder_task = asyncio.create_task(_reminder_loop())
    yield
    # Shutdown.
    reminder_task.cancel()


app = FastAPI(title="Personal To-Do Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (
    health,
    news,
    push,
    tasks,
):
    app.include_router(module.router, prefix="/api")

# Serve the built frontend at / — must be mounted after the /api routers so
# it doesn't shadow them. html=True makes non-file paths fall back to
# index.html. Guarded so `uvicorn` still starts in dev before a build exists
# (use `npm run dev` + the Vite proxy in that case).
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
