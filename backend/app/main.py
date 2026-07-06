"""FastAPI application entrypoint.

Wires routers under /api, CORS for the Vite dev server, creates DB tables on
startup, and serves the built frontend (frontend/dist) at / so the app runs
as a single process.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db import create_db_and_tables
from app.routers import health, news, tasks

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup.
    create_db_and_tables()
    yield


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
    tasks,
):
    app.include_router(module.router, prefix="/api")

# Serve the built frontend at / — must be mounted after the /api routers so
# it doesn't shadow them. html=True makes non-file paths fall back to
# index.html. Guarded so `uvicorn` still starts in dev before a build exists
# (use `npm run dev` + the Vite proxy in that case).
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
