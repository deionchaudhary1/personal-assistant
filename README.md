# Personal To-Do Assistant

A local, single-user, terminal-styled to-do list that turns pasted or typed
text into tasks — with local-LLM task parsing (Ollama) to pull out titles,
priorities, and due dates. One page, one flat list, ordered automatically.

Everything runs on your Mac. The LLM is local (Ollama, `llama3.1:8b`) — no
cloud AI calls, no calendar integration, no notifications.

## Requirements

- Python 3.11+ and Node 18+
- [Ollama](https://ollama.com) with `llama3.1:8b` pulled (optional — the app
  degrades gracefully to a deterministic non-AI fallback if Ollama isn't
  running)

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

## How it works

Deterministic and explainable — the LLM never decides ordering, only
parsing:

1. Add a task with the prompt-style form (title, description, priority,
   due date), or paste free-form to-do text and let Ollama (or the
   deterministic fallback if Ollama isn't running) extract discrete tasks.
2. The list is ordered automatically on every load: **priority
   (high → low), then due date (soonest first, none last), then creation
   time**. High/medium/low rows read in red/yellow/green, terminal-log
   style.
3. Check a task off (`[x]`) to mark it completed — it stays in the list,
   struck through. `[rm]` deletes it. An unfinished task just stays on the
   list, in its sorted position, for as long as it takes.

## Run it as a background app (PWA + LaunchAgent)

For an always-on setup — no terminals, survives reboots, installs like a
Mac app — the backend serves the built frontend directly, so one process
runs everything:

```bash
cd frontend && npm run build   # backend serves whatever is in frontend/dist/
```

**Backend as a login service.** Copy
`backend/deploy/com.personalassistant.backend.plist` to
`~/Library/LaunchAgents/`, replacing `/ABSOLUTE/PATH/TO/personal-assistant`
and `YOUR_USERNAME` with real values, then:

```bash
mkdir -p ~/Library/Logs/personal-assistant
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.personalassistant.backend.plist
```

The server now starts on login and restarts if it crashes (`KeepAlive`).
Logs land in `~/Library/Logs/personal-assistant/`. After pulling code
changes:

```bash
cd frontend && npm run build   # refresh what the backend serves
launchctl bootout gui/$(id -u)/com.personalassistant.backend
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.personalassistant.backend.plist
```

**Install as a PWA.** Open http://localhost:8000 — Safari: **File → Add to
Dock**; Chrome: address-bar install icon → **Install**. Either gives a
standalone window and Dock icon backed by the always-running service.

`npm run dev` (port 5174, proxying `/api` to :8000) still works unchanged
for development.

## Tests

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```

The ordering logic (`backend/app/ordering.py`) is a pure function, so its
tests run with no database, network, or mocks.
