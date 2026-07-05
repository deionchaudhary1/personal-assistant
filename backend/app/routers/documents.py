"""Document ingest, list, delete, and FTS5-backed Q&A."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.documents import ingest, retrieve
from app.llm import ollama_client
from app.llm.ollama_client import OllamaUnavailable
from app.models import Document

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    name: str
    text: str


class QueryRequest(BaseModel):
    question: str


def _doc_to_dict(session: Session, doc: Document) -> dict:
    return {
        "id": doc.id,
        "name": doc.name,
        "created_at": doc.created_at.isoformat(),
        "num_chunks": ingest.count_chunks(session, doc.id),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_document(body: DocumentCreate, session: Session = Depends(get_session)):
    doc = ingest.ingest_document(session, name=body.name, content=body.text)
    return _doc_to_dict(session, doc)


@router.get("")
def list_documents(session: Session = Depends(get_session)):
    docs = session.exec(select(Document).order_by(Document.created_at)).all()
    return [_doc_to_dict(session, d) for d in docs]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, session: Session = Depends(get_session)):
    doc = session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    ingest.delete_document(session, doc)


@router.post("/query")
async def query_documents(body: QueryRequest, session: Session = Depends(get_session)):
    chunks = retrieve.search_chunks(session, body.question, limit=5)
    context = "\n\n---\n\n".join(c["text"] for c in chunks)
    try:
        answer = await ollama_client.answer_question(body.question, context)
    except OllamaUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Document Q&A needs Ollama, which is unavailable: {exc}",
        )
    sources = [
        {"document_name": c["document_name"], "snippet": c["text"][:300]}
        for c in chunks
    ]
    return {"answer": answer, "sources": sources}
