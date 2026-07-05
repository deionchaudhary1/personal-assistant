"""FTS5 retrieval for document Q&A."""

from __future__ import annotations

import re
from typing import Dict, List

from sqlalchemy import text
from sqlmodel import Session

from app.models import Document, DocumentChunk

_TERM_RE = re.compile(r"[A-Za-z0-9]+")


def build_match_query(question: str) -> str:
    """Sanitize a user question into a safe FTS5 MATCH expression.

    Each alphanumeric term is wrapped in double quotes and OR-joined so
    punctuation can never crash the FTS parser.
    """
    terms = _TERM_RE.findall(question or "")
    if not terms:
        return ""
    quoted = [f'"{t}"' for t in terms]
    return " OR ".join(quoted)


def search_chunks(session: Session, question: str, limit: int = 5) -> List[Dict]:
    match_query = build_match_query(question)
    if not match_query:
        return []

    rows = session.exec(
        text(
            "SELECT rowid FROM chunk_fts WHERE chunk_fts MATCH :q "
            "ORDER BY rank LIMIT :lim"
        ).bindparams(q=match_query, lim=limit)
    ).all()

    results: List[Dict] = []
    for row in rows:
        rowid = row[0]
        chunk = session.get(DocumentChunk, rowid)
        if not chunk:
            continue
        doc = session.get(Document, chunk.document_id)
        results.append(
            {
                "document_name": doc.name if doc else "unknown",
                "text": chunk.text,
            }
        )
    return results
