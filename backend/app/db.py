"""Database engine and session dependency."""

from __future__ import annotations

import os
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

# assistant.db lives in the backend/ directory (parent of app/).
# ASSISTANT_DB_PATH overrides it so test/dev servers can run against a
# scratch database without touching the production file.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("ASSISTANT_DB_PATH") or os.path.join(BACKEND_DIR, "assistant.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
