# PARSE.md implementation summary

Implemented 2026-07-06, from `plans/PARSE.md`: a daily AI-news digest
sourced from the arXiv Atom API, shown in a terminal-styled sidebar next to
the to-do list.

## What changed

### Backend
- `app/models/news_item.py` (new): `NewsItem` — source (default
  `"arxiv"`), title, truncated summary, url, published_date, fetched_at.
- `app/models/app_meta.py` (new): single-row `AppMeta(id=1)` with
  `last_news_fetch_date`. **Note:** the plan said to reuse the `AppMeta`
  table from TASK-CARE.md, but that plan is not implemented — the table
  was created fresh here with only the news column, shaped so TASK-CARE
  can add `last_maintenance_date` later. Both new tables are created by
  the existing `create_db_and_tables()` startup hook; no manual migration.
- `app/news/arxiv_client.py` (new): queries
  `export.arxiv.org/api/query` (cs.AI OR cs.LG OR cs.CL, newest first,
  max 5) with httpx, matching `ollama_client`'s style. Atom parsing is a
  pure function (`parse_feed`) over `xml.etree.ElementTree` so tests run
  offline; summaries collapse arXiv's newline wrapping and truncate to
  first sentence or ~200 chars, whichever is shorter.
- `app/news/service.py` (new): `get_digest` lazy catch-up — cached rows
  if already fetched today; otherwise fetch, replace rows, advance the
  date. On fetch failure: log a warning and serve the stale cache (the
  date does not advance, so the next request retries). Never raises to
  the route.
- `app/routers/news.py` (new): `GET /api/news` →
  `{"items": [{title, summary, url, published_date}]}`; registered in
  `main.py`.
- Tests (new): `test_arxiv_client.py` (fixture-based parse/truncation)
  and `test_news_service.py` (no-refetch-same-day, day-advance replace,
  stale-cache-on-failure). Suite: 16/16 pass.

### Frontend
- `components/NewsPanel.tsx` (new): react-query (`["news"]`, 1h
  staleTime) card headed `> ai_news` — title links open the arXiv abs
  page in a new tab (`rel="noreferrer"`), muted summary, small date;
  loading / quiet-error / "no news cached yet" states.
- `App.tsx` + `index.css`: `.app-layout` two-column flex — Tasks fills,
  panel fixed 300px, stacking to one column under 900px; shell max-width
  widened to 1040px. `.news-*` styles follow the task-log treatment
  (monospace, 1px borders, square corners, both themes).

## Deviations / notes
- `AppMeta` created standalone (see above) — TASK-CARE.md remains
  unimplemented and unblocked.
- `reload.sh` hardened while deploying: `launchctl bootstrap` immediately
  after `bootout` can race ("Input/output error"); the script now waits
  2s and retries once.

## Verification
- 16/16 backend tests (offline — parsing and service logic are
  network-free); clean `npm run build`.
- Deployed via `reload.sh` to the live LaunchAgent service and verified
  on :8000: `/api/news` returns 5 real arXiv entries with valid abs-page
  URLs and truncated summaries; `/api/tasks` and the served frontend
  unaffected. (Entries dated a few days back = arXiv's weekend
  announcement gap, not a bug.)
- Not verified here (needs GUI): the rendered panel layout in a browser
  and the simulated-outage UX — the service-level stale-cache path is
  covered by tests.
