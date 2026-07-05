# Personal Scheduling Assistant

A local, single-user web app that turns your to-do list into a time-blocked day/week
schedule — aware of your Google Calendar commitments and working hours — with local-LLM
task parsing (Ollama), native macOS notifications, and an end-of-day review that rolls
unfinished tasks forward by priority.

Everything runs on your Mac. The only external service is Google Calendar (optional).
The LLM is local (Ollama, `llama3.1:8b`) — no cloud AI calls.

## Requirements

- macOS (notifications use `osascript`)
- Python 3.11+ and Node 18+
- [Ollama](https://ollama.com) with `llama3.1:8b` pulled (optional — the app degrades
  gracefully to non-AI fallbacks if Ollama isn't running)

## Run it

Two terminals:

```bash
# Terminal 1 — backend (API on :8000)
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (UI on :5174)
cd frontend
npm run dev
```

Then open http://localhost:5174.

First-time setup, if the environments aren't built yet:

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd frontend && npm install
```

## Google Calendar (optional)

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project,
   enable the **Google Calendar API**, and create an **OAuth client ID** of type
   **Web application** with the authorized redirect URI
   `http://localhost:8000/api/calendar/oauth-callback`.
2. Download the client secret JSON and save it as `backend/credentials.json`.
3. In the app: **Settings → Google Calendar → Connect**, approve in the browser.
4. Events sync automatically every 30 minutes, or via **Sync now**.

Without credentials, everything else works; you can enter busy blocks manually on the
Today page.

## How scheduling works

Deterministic and explainable — the LLM never decides placement:

1. Tasks are ordered by **priority (high → low), then due date, then creation time**.
2. Free slots = working hours − calendar/busy blocks − already-placed blocks
   (today's slots also start no earlier than "now").
3. Greedy first-fit places each task in the first slot it fits; anything that doesn't
   fit is surfaced as "didn't fit today", never silently dropped.
4. **End of Day Review**: check off what you finished; everything else returns to
   pending and is rescheduled from tomorrow onward, re-ordered by the same rule.

## Tests

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```

The scheduling engine (`backend/app/scheduler/engine.py`) is pure — no I/O — so its
tests run with no database, network, or mocks.
