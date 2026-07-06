# Plain to-do list, terminal-styled — remove the scheduler

## Context

After SIMPLIFY.md, the app still round-robins tasks across the 7 days of
the week (`distribute_week` + `Task.scheduled_date` + a "Week" page). The
user wants that gone entirely: one page, one flat to-do list, ordered
automatically by priority and due date, styled to look and feel like a
terminal. "Rollover" — a task that isn't checked off just stays on the
list; there's no day-bucketing left to roll it over *from*, so this falls
out for free once the scheduler is deleted, no extra logic required.

## Behavior spec

- **One page.** The to-do list is the entire app. No nav between pages.
- **Input, exactly 4 fields.** Title, description, priority
  (high/medium/low), due date. Nothing else (no duration estimate, no day
  assignment). This already matches `TaskForm.tsx` as it stands today —
  it only needs a visual restyle, not a field change.
- **Ordering is automatic.** Every render, tasks sort by priority
  (high → medium → low), then due date (soonest first, no-due-date last),
  then creation time as a tiebreak. The user never manually orders or
  assigns a day — this is the existing `order_tasks` logic, just
  detached from the scheduler (see below).
- **Rollover.** A task stays in the list, in its sorted position, for as
  long as it's `pending` — across as many days as it takes. Nothing
  needs to be built for this; it's what happens automatically once
  `scheduled_date`/day-bucketing is removed.
- **Checkbox + strikethrough.** Each row has a checkbox. Checking it
  PATCHes the task to `status: "completed"`; the title gets a
  strikethrough and mutes to a dim/gray tone (still visible in the list —
  nothing here calls for auto-hiding or deleting completed tasks).
- **Priority color coding.** Not a small badge tag — the task line itself
  reads in its priority color: high = red, medium = yellow, low = green.
  Applies to the whole visible row (title + a `[high]`-style tag), so the
  urgency is readable at a glance down the list, terminal-log style.
- **Terminal look.** Monospace type throughout, dark background,
  sharp/square corners (no rounded cards, no gradients or glow — flat and
  authentic), 1px or box-drawing-style borders, a blinking-cursor input
  prompt for adding a task (e.g. `> new task_`), and a `[ ]` / `[x]`
  reading for checkboxes rather than a native rounded checkbox. Keep the
  existing light/dark theme switching infrastructure in `index.css` (CSS
  vars driven by `prefers-color-scheme`), just re-skin both variants in
  the terminal palette (dark: near-black bg / phosphor-green or amber
  accent; light: paper bg / dark monospace text) instead of introducing a
  single forced theme.

## Backend changes

- `app/models/task.py`: remove `scheduled_date`.
- `app/ordering.py` (new): `order_tasks(tasks: List[Task]) -> List[Task]`
  — the same priority/due_date/created_at sort that lives in
  `scheduler/engine.py` today, moved out and operating directly on `Task`
  rows (no more `SchedulableTask` adapter — that indirection existed only
  for the scheduler's from-scratch I/O-free tests, and there's no
  scheduler left to justify it).
- `app/routers/tasks.py`: inline `task_to_dict` (currently in
  `scheduler/service.py`, and this is its only remaining caller, dropping
  the `scheduled_date` key); `list_tasks` sorts via
  `ordering.order_tasks(tasks)` directly.
- Delete `app/scheduler/` (engine.py, service.py, `__init__.py`) and
  `app/routers/schedule.py` entirely.
- `app/main.py`: drop the `schedule` router import/registration.
- `backend/tests/`: delete `test_scheduler_engine.py`; add
  `test_ordering.py` covering the same three cases (priority rank,
  due-date-none-last, created_at tiebreak).
- **DB migration**: `backend/assistant.db` has the old schema with
  `scheduled_date`. Drop that column in place (back up the file first,
  same approach as the SIMPLIFY.md migration).

## Frontend changes

- Delete `frontend/src/pages/Week.tsx`.
- `App.tsx`: no router needed — render the to-do list directly (or keep
  a single `/` route if you want to preserve `react-router-dom`, but no
  second route/nav links exist to justify it).
- `api/client.ts` / `api/types.ts`: remove `getWeekSchedule`/`runSchedule`,
  `DaySchedule`, `ScheduleRunResult`; drop `scheduled_date` from `Task`.
- `pages/Tasks.tsx` (becomes the app's only page/component):
  - Add a checkbox to each row (reuse the toggle-to-`completed` mutation
    pattern currently in `Week.tsx`, since that page is going away).
  - Replace the plain `<table>` row rendering with a terminal-log-style
    list: `[ ]`/`[x]` reading, title (struck through + dimmed when done),
    priority tag + due date, colored per-priority as specified above.
  - Keep the existing "paste to-do list" AI-parse flow (Ollama) and the
    new-task form as they are functionally — both already only deal in
    title/description/priority/due_date — just restyle both to match the
    terminal aesthetic (prompt-style labels, square inputs, monospace).
- `index.css`: re-skin `:root` / dark-mode CSS vars for the terminal
  palette; replace `.priority-badge`/`.priority-*` with row-level color
  classes; drop border-radius across cards/inputs/buttons for square
  edges; style checkboxes as bracket characters; add a blinking-cursor
  style for the task-title input. Use the `craft` skill during this pass
  to keep the visual language disciplined (flat colors, no gradients/glow,
  consistent spacing) rather than ad hoc.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/ -q` — ordering tests
  pass, no scheduler tests remain.
- `cd backend && .venv/bin/python -c "import app.main"` — imports cleanly.
- `cd frontend && npm run build` — zero TypeScript errors.
- Grep both trees for `scheduled_date`, `distribute_week`, `schedule/run`,
  `schedule/week`, `Week.tsx` to confirm nothing was left dangling.
- Run the app end-to-end: add a task via the prompt-style form, paste a
  messy list to parse, check one off (confirm strikethrough), add a
  high/medium/low mix and confirm red/yellow/green ordering top-to-bottom,
  confirm no console/network errors reference `/schedule`.
