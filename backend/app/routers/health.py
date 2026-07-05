"""Health check."""

from __future__ import annotations

from fastapi import APIRouter

from app.llm import ollama_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"ok": True, "ollama": await ollama_client.is_up()}
