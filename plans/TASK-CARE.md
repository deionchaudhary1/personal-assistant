# Task lifecycles: daily-continuous, rollover, and midnight-expiring

## Context

Today every task behaves the same way: it sits in the list until you
check it off or delete it (TODO.md's "rollover" behavior — nothing
auto-removes anything). The user wants two more lifecycles alongside
that default:

1. **Continuous** — a task that shows up every day, like a habit
   checkbox (e.g. "workout"). Checking it off marks today's instance
   done, but it must never disappear — at midnight its checkbox resets
   to unchecked so it's ready for tomorrow.
2. **Expiring (today-only)** — a task that is *not* continuous and *not*
   rollover: something only relevant for the day it was added. If it's
   still around at midnight — done or not — it gets deleted outright.

Rollover stays the default (unchanged, matches current/existing tasks).
Manual delete (the `[rm]` button / `DELETE /tasks/{id}`) is untouched and
stays available for every task regardless of lifecycle — the "midnight
delete" described here is a new *automatic* deletion path for expiring
tasks specifically, not a replacement for manual delete.

## Data model

- `app/models/task.py`: add `lifecycle: str = "rollover"` —
  `"continuous" | "rollover" | "expire"`. Default preserves current
  behavior for every existing task with no data change needed beyond
  adding the column.
- Migration: `backend/assistant.db` already has real tasks. Back it up,
  then `ALTER TABLE task ADD COLUMN lifecycle TEXT NOT NULL DEFAULT
  'rollover'` in place (same pattern as the prior SIMPLIFY.md migration).

## Midnight maintenance — lazy catch-up, not a cron job

The backend now runs continuously via the LaunchAgent (PWA.md), but a
laptop sleeps and `launchd` isn't guaranteed to fire something at the
exact stroke of midnight — so rather than adding a scheduler dependency
(APScheduler, previously removed on purpose), maintenance runs as a
**lazy catch-up check**: whenever the task list is next read, if the
calendar day has moved on since the last time maintenance ran, run it
once before returning results. This is simpler, has no new dependency,
and is correct regardless of whether the app was open at midnight.

- New tiny table, `app/models/app_meta.py`: `AppMeta(id=1 fixed,
  last_maintenance_date: date)` — a single row tracking the last day
  maintenance ran.
- New `app/maintenance.py`:
  ```python
  def run_midnight_maintenance(session: Session) -> None:
      """If the calendar day has advanced since last run, reset continuous
      tasks and delete expired ones. No-op if already run today."""
  ```
  Logic: load (or create, seeded to today) the `AppMeta` row; if
  `last_maintenance_date >= today`, return. Otherwise:
  - `UPDATE task SET status = 'pending' WHERE lifecycle = 'continuous' AND status = 'completed'`
    — today's checkmark clears, the task itself is untouched.
  - `DELETE FROM task WHERE lifecycle = 'expire'` — anything not
    continuous/rollover that made it past midnight is gone, regardless of
    whether it was checked off.
  - Set `last_maintenance_date = today`, commit.
- Call `run_midnight_maintenance(session)` at the top of `GET /tasks`
  (`app/routers/tasks.py::list_tasks`) — the one read path the frontend
  always hits (including right after every mutation, via
  `invalidateQueries`), so the list is never stale by more than one
  request.

## Backend API changes

- `TaskCreate` / `TaskUpdate` (in `app/routers/tasks.py`): add
  `lifecycle: str = "rollover"` (create) / `Optional[str]` (update).
- `task_to_dict`: include `lifecycle` in the serialized shape.
- `app/ordering.py`: no change to sort key — lifecycle doesn't affect
  priority/due-date ordering, continuous and expiring tasks sort
  alongside everything else.

## Frontend changes

- `api/types.ts`: add `Lifecycle = "continuous" | "rollover" | "expire"`;
  add `lifecycle: Lifecycle` to `Task` and `TaskDraft`.
- `api/client.ts`: add `lifecycle?: Lifecycle` to `CreateTaskBody`.
- `TaskForm.tsx`: add a lifecycle selector alongside priority/due date —
  a `<select>` with labels `daily` / `rollover` (default) / `today only`,
  mapping to `continuous` / `rollover` / `expire`. This is a deliberate
  5th field, extending TODO.md's original 4-field spec for this feature.
- `pages/Tasks.tsx`:
  - `TaskRow`: show a small tag next to continuous tasks (e.g.
    `[daily]`, styled like the existing `[priority]` tag) so recurring
    habits are visually distinct in the log-style list. Rollover tasks
    keep the current plain look (no new tag, since it's the default).
    Optionally tag `expire` tasks (e.g. `[today]`) so it's clear they
    won't survive midnight.
  - The "paste to-do list" draft review table gets the same lifecycle
    `<select>` per row (parsed drafts default to `rollover`, since intent
    can't be reliably inferred from free text — the user adjusts before
    adding, same pattern already used for priority/due-date there).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/ -q` — add a
  `test_maintenance.py` covering: continuous task with `status=completed`
  resets to `pending` after a simulated day change; an `expire` task is
  deleted after a simulated day change; a `rollover` task is untouched in
  both cases; maintenance is a no-op if called twice the same day.
- Manual run: create one task of each lifecycle, mark them all
  completed, hand-edit `AppMeta.last_maintenance_date` to yesterday (or
  just wait for real midnight), hit `GET /api/tasks`, and confirm: the
  continuous task reappears unchecked, the expiring task is gone, the
  rollover task is still there and still checked off.
- Confirm manual delete (`[rm]`) still works immediately on any task
  regardless of lifecycle, independent of the midnight logic.
