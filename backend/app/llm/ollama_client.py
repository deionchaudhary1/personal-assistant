"""Async Ollama client with robust fallbacks.

The parse call MUST never raise to the caller in a way that produces a 500 —
callers use the deterministic fallback.
"""

from __future__ import annotations

import json
import re
from datetime import date as Date
from typing import Any, Dict, List, Optional

import httpx

from app.llm import prompts

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"
TIMEOUT = 90.0

_VALID_PRIORITIES = {"high", "medium", "low"}


async def _chat(messages: List[Dict[str, str]], json_format: bool) -> str:
    payload: Dict[str, Any] = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }
    if json_format:
        payload["format"] = "json"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return data.get("message", {}).get("content", "")


async def is_up() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Deterministic fallbacks
# ---------------------------------------------------------------------------

_BULLET_RE = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s*")


def fallback_parse(text: str) -> List[Dict[str, Any]]:
    drafts: List[Dict[str, Any]] = []
    for line in text.splitlines():
        stripped = _BULLET_RE.sub("", line).strip()
        if not stripped:
            continue
        drafts.append(
            {
                "title": stripped,
                "description": None,
                "priority": "medium",
                "due_date": None,
            }
        )
    return drafts


def _coerce_due_date(value: Any) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = Date.fromisoformat(value)
    except ValueError:
        return None
    # 8B models happily hallucinate past deadlines; a past due date is never
    # useful for scheduling, so drop it rather than surface it.
    if parsed < Date.today():
        return None
    return value


def _sanitize_draft(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    priority = raw.get("priority")
    if priority not in _VALID_PRIORITIES:
        priority = "medium"
    description = raw.get("description")
    if not isinstance(description, str):
        description = None
    return {
        "title": title.strip(),
        "description": description,
        "priority": priority,
        "due_date": _coerce_due_date(raw.get("due_date")),
    }


# ---------------------------------------------------------------------------
# Public calls
# ---------------------------------------------------------------------------


async def parse_tasks(text: str) -> List[Dict[str, Any]]:
    """Return a list of TaskDraft dicts. Never raises; falls back on any error."""
    try:
        content = await _chat(
            [
                {"role": "system", "content": prompts.PARSE_SYSTEM},
                {"role": "user", "content": prompts.parse_user_prompt(text)},
            ],
            json_format=True,
        )
        data = json.loads(content)
        raw_drafts = data.get("drafts")
        if not isinstance(raw_drafts, list):
            raise ValueError("no drafts list")
        cleaned = [d for d in (_sanitize_draft(r) for r in raw_drafts if isinstance(r, dict)) if d]
        if not cleaned:
            raise ValueError("no valid drafts")
        return cleaned
    except Exception:
        return fallback_parse(text)
