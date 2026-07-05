"""Document chunking and FTS5 index management."""

from __future__ import annotations

from typing import List

from sqlalchemy import text
from sqlmodel import Session, select

from app.models import Document, DocumentChunk

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150


def create_fts_table(session: Session) -> None:
    """Create the external-content FTS5 virtual table mirroring documentchunk."""
    session.exec(
        text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5("
            "text, "
            "content='documentchunk', "
            "content_rowid='id'"
            ")"
        )
    )
    session.commit()


def chunk_text(content: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    content = content or ""
    if not content.strip():
        return []
    chunks: List[str] = []
    step = max(1, size - overlap)
    start = 0
    n = len(content)
    while start < n:
        chunk = content[start : start + size]
        if chunk.strip():
            chunks.append(chunk)
        if start + size >= n:
            break
        start += step
    return chunks


def _index_chunk(session: Session, chunk: DocumentChunk) -> None:
    session.exec(
        text("INSERT INTO chunk_fts(rowid, text) VALUES (:rid, :txt)").bindparams(
            rid=chunk.id, txt=chunk.text
        )
    )


def _unindex_chunk(session: Session, chunk: DocumentChunk) -> None:
    # 'delete' command for external-content FTS5 tables.
    session.exec(
        text(
            "INSERT INTO chunk_fts(chunk_fts, rowid, text) "
            "VALUES ('delete', :rid, :txt)"
        ).bindparams(rid=chunk.id, txt=chunk.text)
    )


def ingest_document(session: Session, name: str, content: str) -> Document:
    doc = Document(name=name)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    for idx, piece in enumerate(chunk_text(content)):
        chunk = DocumentChunk(document_id=doc.id, chunk_index=idx, text=piece)
        session.add(chunk)
        session.commit()
        session.refresh(chunk)
        _index_chunk(session, chunk)
    session.commit()
    return doc


def delete_document(session: Session, doc: Document) -> None:
    chunks = session.exec(
        select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    ).all()
    for chunk in chunks:
        _unindex_chunk(session, chunk)
        session.delete(chunk)
    session.delete(doc)
    session.commit()


def count_chunks(session: Session, document_id: int) -> int:
    chunks = session.exec(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    ).all()
    return len(chunks)
