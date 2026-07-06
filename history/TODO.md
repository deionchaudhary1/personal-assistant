# TODO.md implementation summary

Implemented 2026-07-06, from `plans/TODO.md`: removed the week scheduler
entirely and reduced the app to a single terminal-styled to-do list.

## What changed

### Backend
- `Task.scheduled_date` removed from the model; the column was dropped from
  `backend/assistant.db` in place (file backed up before the migration;
  existing tasks preserved).
- New `app/ordering.py`: `order_tasks` sorts `Task` rows directly by
  priority rank (high → medium → low) → due date (soonest first, none
  last) → `created_at`. The `SchedulableTask` adapter is gone with the
  scheduler that justified it.
- `app/scheduler/` (engine, service) and `app/routers/schedule.py`
  deleted; `main.py` registers only the health and tasks routers.
- `routers/tasks.py` inlines `task_to_dict` (no `scheduled_date` key) and
  sorts `GET /tasks` responses via `order_tasks`.
- Tests: `test_scheduler_engine.py` deleted; new `test_ordering.py`
  (5 tests) covers priority ranking, due-date none-last, and the
  created-at tiebreak.

### Frontend
- Single page, no router: `App.tsx` renders the to-do page directly;
  `Week.tsx` and `PriorityBadge.tsx` deleted; `getWeekSchedule`,
  `runSchedule`, `DaySchedule`, `ScheduleRunResult`, and
  `Task.scheduled_date` removed from the API layer.
- `Tasks.tsx` is the whole app: a terminal-log task list with `[ ]`/`[x]`
  bracket checkboxes (PATCH toggles pending/completed), strikethrough +
  dimming on completed rows, whole-row priority coloring (high=red,
  medium=yellow, low=green), a `[rm]` delete control per row, the 4-field
  new-task form (`> new_task` prompt style, blinking-caret title input),
  and the Ollama paste-to-parse flow with an editable draft review table.
- `index.css` re-skinned on the existing `prefers-color-scheme` CSS-var
  infrastructure: dark = near-black with phosphor-green accent, light =
  paper with dark mono text; monospace throughout, square corners, 1px
  borders, no gradients/shadows.

## Deviations from the plan
- **Restored task deletion.** The row spec (checkbox/title/tag/due) didn't
  mention the pre-existing Edit/Delete controls and the first pass dropped
  both, leaving no way to remove a task. A terminal-styled `[rm]` button
  was added back per row. Post-creation *editing* (title/priority/due) is
  still gone — rows are toggle/delete only; re-add via the form if needed.
- **README rewritten** (not in the plan): the "How scheduling works"
  section described the deleted round-robin scheduler; it now documents
  the flat auto-ordered list, and the title changed from "Personal
  Scheduling Assistant" to "Personal To-Do Assistant".

## Verification
- `pytest tests/ -q`: 5/5 pass; `from app.main import app` imports clean.
- `npm run build`: zero TypeScript errors.
- Greps for `scheduled_date`, `distribute_week`, `schedule/run`,
  `schedule/week`, `Week.tsx`, `DaySchedule`, `SchedulableTask` across
  `backend/`, `frontend/src/`, and README: zero hits.
- Live API smoke test: created high/low tasks → `GET /tasks` returned
  correct order (high first, due-date-none-last among mediums, low last);
  PATCH toggled to completed; DELETE returned 204; `/api/schedule/*`
  routes 404. Personal tasks ("leetcode", "prep for 189") intact after
  cleanup.
- Not done: no browser-level visual check of the terminal theme — verify
  with `npm run dev` + backend on :8000.
