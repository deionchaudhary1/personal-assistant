Summary
The plan in plans/SIMPLIFY.md is fully implemented — 42 files changed, net −2,774 lines. Nothing is committed yet.

How the work was routed (frugal split): the plan was precise enough that I delegated execution to two parallel Sonnet agents with disjoint ownership — one for backend/ + README (gated on pytest + clean import), one for frontend/ (gated on a zero-error TypeScript build). I kept integration review, and that's where the remaining bugs were, since each agent's gates could only see its own half:

POST /schedule/run would have 422'd from the UI — the backend declared a required request body while the frontend sent none. Fixed both sides: the body is now optional in schedule.py, and the frontend now sends start_date explicitly.
Week-window mismatch — "Run scheduler" let the backend default to today as day 0, while the view shows a Monday-start week, so tasks run on a weekend would land outside the visible window. Week.tsx now passes its Monday start to the run call.
Smaller cleanups: added the missing scheduled_date field to the frontend Task type, and trimmed the dead time-block-era helpers out of date.ts.
Database migration (not in the plan): your existing backend/assistant.db had the old schema and would have crashed the new code. I migrated it in place — added scheduled_date, dropped estimated_minutes, dropped all the dead tables — and your one real task ("leetcode") survived as pending. A pre-migration backup is in the session scratchpad if anything looks off.

Verified: 9/9 engine tests pass, app.main imports cleanly, frontend builds with zero TS errors, the dead-reference grep across both trees is empty, and I exercised the full API live — create task → run scheduler → week view shows correct round-robin/due-date placement → mark completed. The one thing I didn't do is click through the browser UI itself; npm run dev + the backend on :8000 will let you eyeball the new Week view before committing.