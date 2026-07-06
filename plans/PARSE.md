# Daily AI-news digest from arXiv

## Context

The user wants a side panel added to the app — alongside the to-do
list — showing a daily digest of AI news: title, brief description, and
a clickable link, sourced from arxiv.org (other sources may follow
later, hence "for now"). arXiv doesn't have a "news" feed, but it has a
public Atom API for querying recent papers by category, which is a much
better fit than scraping HTML — structured, stable, and it's the
intended integration point.

Decisions confirmed with the user:
- **Description**: truncate each paper's abstract (first sentence /
  ~200 chars) rather than summarizing with the local Ollama model — no
  new LLM dependency for this feature, instant, no daily fetch latency.
- **Categories**: `cs.AI`, `cs.LG`, `cs.CL` (the three that cover
  mainstream AI/ML/LLM papers).
- **Digest size**: 5 papers/day.

## Fetch source

arXiv's export API: `http://export.arxiv.org/api/query` with
`search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=5`,
returning an Atom XML feed. Each `<entry>` gives `title`, `summary`
(abstract), `id` (the arxiv.org abs-page URL — the clickable link),
and `published`.

## Daily refresh — same lazy catch-up pattern as TASK-CARE.md

No new scheduler dependency (consistent with the reasoning in
TASK-CARE.md: `launchd` isn't guaranteed to fire exactly on schedule
through sleep, so lazy catch-up on read is simpler and more robust than
a cron job). Whenever the digest is requested, if the calendar day has
moved on since the last successful fetch, re-fetch and replace the
cached entries; otherwise serve what's cached.

- New model, `app/models/news_item.py`: `NewsItem` — `id`, `source`
  (`"arxiv"`, for future sources), `title`, `summary` (truncated),
  `url`, `published_date`, `fetched_at`.
- Reuse or extend the `AppMeta` single-row table from TASK-CARE.md with
  a `last_news_fetch_date` column (rather than a second meta table) —
  same catch-up mechanism, one place tracking "what ran today."
- New `app/news/arxiv_client.py`:
  ```python
  async def fetch_daily_digest() -> List[Dict]:
      """Query the arXiv API, parse the Atom feed, return up to 5
      {title, summary, url, published_date} dicts. Raises on
      network/parse failure — caller decides the fallback."""
  ```
  Parse the Atom XML with the standard library (`xml.etree.ElementTree`
  — no new dependency), truncate each `summary` to its first sentence or
  ~200 chars (whichever is shorter), strip the arXiv abstract's newline
  wrapping.
- New `app/news/service.py`:
  ```python
  async def get_digest(session: Session) -> List[Dict]:
      """Lazy catch-up: if AppMeta.last_news_fetch_date < today, call
      fetch_daily_digest(), replace the NewsItem rows, update the date.
      On fetch failure, log and fall through to serving whatever's
      cached (even if stale) rather than erroring the page — same
      never-break-the-UI posture as ollama_client.parse_tasks."""
  ```

## Backend API

- New router `app/routers/news.py`: `GET /api/news` → `get_digest`,
  returns `{"items": [{"title", "summary", "url", "published_date"}]}`.
- Register it in `app/main.py` alongside `health`/`tasks`.

## Frontend changes

- New `frontend/src/pages/NewsPanel.tsx` (or `components/NewsPanel.tsx`
  — it's a fixed panel, not a route, since this stays a single-page
  app): fetches `GET /api/news` via `@tanstack/react-query`
  (`queryKey: ["news"]`, a `staleTime` of an hour or so is enough since
  the backend itself only refreshes once a day), renders up to 5 items:
  title, truncated description, and the arXiv link opened in a new tab
  (`target="_blank" rel="noreferrer"`).
- `App.tsx`: change `.app-main` from a single column to a two-column
  layout — the existing `<Tasks />` on the left/main area, `<NewsPanel
  />` as a fixed-width sidebar on the right. Keep it terminal-styled to
  match TODO.md's aesthetic (monospace, square borders, same palette) —
  visually it should read as another `card`/log panel, e.g. headed
  `> ai_news`.
- `index.css`: add a `.app-layout` (flex row, `Tasks` flexed to fill,
  `NewsPanel` fixed ~280–320px) and `.news-item` styles (title, muted
  truncated summary, link) consistent with the existing `.task-log`/
  `.task-row` treatment.
- `api/types.ts` / `api/client.ts`: add `NewsItem` type and
  `getNews(): Promise<{ items: NewsItem[] }>`.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/ -q` — add
  `test_arxiv_client.py` (parse a sample Atom XML fixture into the
  expected dicts, confirm truncation) and a `test_news_service.py`
  covering the same lazy-catch-up cases as `test_maintenance.py`: no
  fetch if already run today, fetch + replace if the day advanced,
  serve stale cache on fetch failure rather than raising.
- `curl -s http://localhost:8000/api/news | python -m json.tool` —
  confirm 5 real arXiv entries with working `url`s.
- `cd frontend && npm run build` — zero TypeScript errors.
- Load the app: confirm the side panel renders 5 titles + descriptions,
  each link opens the correct arxiv.org abstract page in a new tab, and
  a simulated arXiv-API outage (e.g. block the host) still shows
  yesterday's cached digest instead of an error state.
