# Simplify to: text box → week's to-do list

## Context

The app today is a full time-blocking scheduler: it places tasks into exact
start/end slots against Google Calendar busy blocks and per-day working
hours, sends native macOS notifications when a block starts, polls Google
Calendar every 30 minutes, supports a documents/RAG Q&A feature, and has an
end-of-day review + rollover flow. The user wants the model reduced to its
essence: type/paste text into a box, get a to-do list spread across the
coming week — no exact times, no calendar, no notifications, no documents.

Decisions confirmed with the user:
- **Scheduling**: drop exact time-blocking entirely. Replace with simple day
  buckets (Mon–Sun) — no working hours, no calendar/busy-block awareness.
- **Parsing**: keep the Ollama LLM call that turns pasted text into
  discrete tasks (title/priority/due date), with its existing deterministic
  fallback if Ollama isn't running.
- **Removed entirely**: Google Calendar sync, native notifications,
  documents/RAG Q&A, end-of-day review/rollover, working hours, busy blocks,
  time-block precision (start/end times).

Since duration estimates only ever fed the time-slot placement engine (which
is going away), the "estimate with AI" feature and `estimated_minutes` field
are dead weight under the new model — plan removes them too. Flagging this
so it can be vetoed, but it's a direct consequence of dropping time-blocking.

## New shape

**Backend model**: `Task` keeps `title`, `description`, `priority`,
`due_date`, `status` (`pending`/`completed`), `created_at`, `source`; gains
`scheduled_date: Optional[date]` (which day of the current week it's
assigned to). `TimeBlock`, `BusyBlock`, `WorkingHours`, `Document`,
`DocumentChunk`, `OAuthToken` models are deleted.

**New engine** (`backend/app/scheduler/engine.py`, rewritten, still pure/
no I/O): keep `order_tasks` (priority → due_date → created_at) since it's
reused. Replace the slot/interval machinery with:
```python
def distribute_week(start_day: Date, tasks: List[SchedulableTask]) -> Dict[int, List[SchedulableTask]]
```
Round-robins the ordered tasks across the 7 days of the week (day 0 = 1st
highest-priority task, day 1 = 2nd, … wrapping after day 6), so higher-
priority items land earlier in the week and load is spread evenly. If a
task has a `due_date` inside the week, cap its assigned day to
`min(round_robin_day, due_date)` so it never gets placed after its deadline.

**Service layer** (`backend/app/scheduler/service.py`, rewritten): DB glue
that loads pending tasks, calls `distribute_week`, writes `scheduled_date`
directly onto `Task` rows (no separate block table), and serializes
`{"days": [{"date": ..., "tasks": [...]}, ...]}` for the week view.
`rollover.py` is deleted — since there's no per-day "done/skipped" status
tied to a block, unfinished tasks just stay `pending` and get redistributed
next time the week is (re)run.

**Routers**:
- `tasks.py`: keep CRUD + `/tasks/parse` (Ollama). Drop `/tasks/estimate`.
- `schedule.py`: keep `GET /schedule/week` and `POST /schedule/run`
  (always scope="week" now — drop the day/week scope distinction and
  `/schedule/day`, `/schedule/blocks/{id}` PATCH, `/schedule/end-of-day`).
- Delete `busy_blocks.py`, `calendar.py`, `documents.py`, `settings.py`
  routers entirely, and their `main.py` registrations.

**LLM layer**: `ollama_client.py` keeps `parse_tasks`/`fallback_parse`;
drop `estimate_minutes` and `answer_question` (doc Q&A) and `is_up`'s only
consumer (health check — keep `is_up`, used by `/health`). `prompts.py`
keeps `PARSE_SYSTEM`/`parse_user_prompt`; drop `ESTIMATE_SYSTEM`/
`estimate_user_prompt`/`QA_SYSTEM`/`qa_user_prompt`, and drop
`estimated_minutes` from the parse JSON schema and `_sanitize_draft`.

**Deleted wholesale**: `app/calendar_sync/`, `app/documents/`,
`app/notifications/` (notifier + scheduler_job/APScheduler wiring),
`app/scheduler/rollover.py`. `main.py` loses the APScheduler lifespan
wiring (calendar poll, 21:00 safety net, per-block notify jobs), the
working-hours seeding, and the FTS5 table creation — becomes a plain
startup that just creates tables.

**requirements.txt**: drop `apscheduler`, `google-api-python-client`,
`google-auth-oauthlib`.

**Frontend**:
- `App.tsx`: nav becomes **Week** (home, `/`) and **Tasks** (`/tasks`)
  only. Delete `Today.tsx`, `Documents.tsx`, `Settings.tsx` routes.
- `Week.tsx`: rewritten as the main to-do view — 7 day columns (Mon–Sun),
  each listing its assigned tasks as a plain checklist (title, priority
  badge, due date, checkbox to mark done → `PATCH /tasks/{id}`), a "Didn't
  fit" panel is no longer needed (day buckets always fit everything), and a
  "Run scheduler" button to redistribute all pending tasks.
- `Tasks.tsx`: keep as the backlog manager (existing all-tasks table +
  "Paste to-do list" → Ollama parse → review/edit drafts → add). Remove
  the `estimated_minutes` column/inputs throughout.
- `TaskForm.tsx`: drop the estimated-minutes field and "Estimate with AI"
  button/handler.
- Delete `TimeBlockGrid.tsx`, `EndOfDayReview.tsx`, `Today.tsx`,
  `Documents.tsx`, `Settings.tsx`.
- `api/client.ts` / `api/types.ts`: remove busy-block, calendar, documents,
  working-hours, `estimateTask`, `patchBlock`, `endOfDay` functions/types;
  `TimeBlock`/`BusyBlock`/`WorkingHoursDay`/`Document*`/`CalendarStatus`
  types removed; `DaySchedule` becomes `{ date: string; tasks: Task[] }`;
  `Task` drops `estimated_minutes`, `status` becomes `"pending" |
  "completed"`.

**Tests**: rewrite `backend/tests/test_scheduler_engine.py` for
`order_tasks` + `distribute_week` (round-robin ordering, due-date capping),
dropping all slot/interval/working-window tests.

**README.md**: rewrite the "How scheduling works" and setup sections to
describe the simplified flow (paste text → parse → week to-do list; no
calendar, no notifications, no documents) and drop the Google Calendar
setup section entirely.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/ -q` — engine tests pass.
- `cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000` starts
  cleanly with no APScheduler/calendar/document imports.
- `cd frontend && npm run dev` — add a task via the paste box, confirm it
  appears in the week view under a day, mark it done, click "Run
  scheduler" and confirm redistribution works with no console errors.
- Grep for now-dead references (`TimeBlock`, `BusyBlock`, `WorkingHours`,
  `calendar_sync`, `notifications`, `documents`, `estimated_minutes`) across
  both `backend/` and `frontend/src/` to confirm nothing was left dangling.
