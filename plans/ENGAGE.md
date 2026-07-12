# Multi-source digest, read streaks, a pet, and a more native phone app

## Goal

Four things, in service of one habit: open the app daily and actually read
your updates.

1. **More sources.** The digest (PARSE.md) is arXiv-only today. Make it
   pluggable so Hacker News, AI-lab blogs, etc. can sit alongside arXiv
   without rewriting the fetch/cache machinery each time.
2. **Notifications.** A real push notification — reaching the phone/Mac
   even when the app isn't open — nudging you to read today's digest.
3. **Streak + pet.** Reading everything in a day's digest extends a
   streak; the streak grows a small terminal-styled pet. Missing a day
   pauses growth instead of deleting progress.
4. **A phone app that feels like an app.** Push notifications, a Home
   Screen unread badge, and native-feel chrome (safe-area insets, no
   browser bounce) — the gap between "PWA" and "real app" that's still
   open after PWA.md/MOBILE.md.

## Approach

### 1. Multi-source digest: adapter registry vs. one-off scripts

| | One-off per source (today's pattern) | Adapter registry |
|---|---|---|
| Adding a source | Copy `arxiv_client.py`, hand-wire into `service.py` | Drop a new file implementing one small interface, add it to a list |
| Per-source cadence | Single `AppMeta.last_news_fetch_date` — same refresh interval forced on every source | Each source tracks its own last-fetch time; arXiv can stay daily while Hacker News refreshes hourly |
| Failure isolation | N/A (only one source) | One source failing (timeout, bad XML) doesn't blank out the others |

**Recommended: adapter registry.** PARSE.md's `NewsItem.source` field
already anticipated this ("arxiv", for future sources) — this plan follows
through on it. `AppMeta.last_news_fetch_date` is replaced by a small
per-source state table (see Changes Required); this is a deliberate, small
break from PARSE.md's original schema.

### 2. Notifications: Web Push vs. in-app banner vs. email

| | In-app banner only | Email digest | Web Push |
|---|---|---|---|
| Reaches you when the app is closed | No | Yes | Yes |
| New infrastructure | None | Needs an email-sending service (cost, deliverability) | Browser-vendor push relay — free, no account |
| Fits "app notification" as asked | No | Not really — it's email | Yes |

**Recommended: Web Push**, via a service-worker `push` event and VAPID
keys. This is the one piece of this plan that **reverses an earlier
decision**: SIMPLIFY.md removed APScheduler and TASK-CARE.md deliberately
chose lazy catch-up over a scheduler, reasoning that "the backend isn't
guaranteed to run exactly on time, so make correctness independent of
timing." That reasoning doesn't apply here — a push notification is
inherently proactive (the whole point is reaching a *closed* app), so
there's no lazy equivalent. This plan adds the smallest possible
scheduled primitive to make that possible: one `asyncio` background loop
in the FastAPI lifespan (no APScheduler, no new process manager),
checked in the Cost & Services / Changes sections below. Task-list
maintenance stays lazy exactly as TASK-CARE.md designed it — this
exception is scoped to push only.

**Requires HTTPS.** Right now the phone reaches the app over plain HTTP
at a LAN IP (`http://10.44.124.216:8000`, set up ad hoc this session).
Web Push requires a "secure context" — the browser will not let a page
subscribe to push over plain HTTP from another device. MOBILE.md already
identified this gap and filed it as an optional follow-up
("`tailscale serve`/`tailscale cert` ... out of scope for the initial
phone-via-Safari setup"). **This plan promotes that follow-up to a hard
prerequisite** — Step 1 below adopts MOBILE.md's Tailscale setup (if not
already done) and layers `tailscale cert` on top so the phone reaches the
app over real HTTPS at a stable tailnet hostname. (MOBILE.md is annotated
to point here — see the note added to that file.)

### 3. Streak + pet: server-tracked vs. client-only

| | Client-only (localStorage) | Server-tracked |
|---|---|---|
| Survives switching devices (phone ↔ Mac) | No — separate streak per device | Yes — same as every other piece of state in this app |
| Consistent with the rest of the app | No | Yes (MOBILE.md: "one SQLite DB, one backend, two clients") |

**Recommended: server-tracked**, one singleton `Engagement` row, same
shape as `AppMeta`. The pet itself is small monospace ASCII art rendered
in CSS/text — no image assets, no art pipeline, consistent with how the
PWA icon (PWA.md) was hand-drawn as flat SVG rather than sourced.

**Design for the streak:** reading *every* item in a day's digest before
the day ends extends the streak by one. Missing a day **stalls** growth
and dents the pet's happiness — it does not erase the streak count
retroactively below what was already earned, and there's no permanent
"game over." This is a personal-productivity nudge, not a punishing game.

### 4. Native-feel phone app: keep the PWA vs. a native wrapper

PWA.md already ruled out a native shell (Tauri) for the desktop menu-bar
idea, for the same reason it applies here: a native wrapper (Capacitor,
React Native) is new code to build and maintain, a build pipeline, and
(for iOS) a $99/yr Apple Developer Program account just to sideload/
distribute it. **Recommended: keep extending the PWA.** Web Push
(above) closes the single biggest gap versus a native app; a Home Screen
unread badge (Badging API) and safe-area/status-bar CSS close most of the
rest, for zero additional cost or build tooling.

## Changes Required

### Backend — multi-source digest

- `app/news/sources/base.py` (new): a small `Protocol`/ABC — `name: str`,
  `refresh_interval: timedelta`, `async def fetch() -> List[Dict]`
  returning `{title, summary, url, published_date}` dicts (matches
  `NewsItem`'s existing shape).
- `app/news/sources/arxiv.py` (moved from `app/news/arxiv_client.py`):
  same logic, wrapped to satisfy the interface, `refresh_interval=24h`.
- `app/news/sources/hackernews.py` (new): Hacker News via the free,
  keyless Algolia HN Search API (`https://hn.algolia.com/api/v1/search`,
  front-page or an AI-keyword query), `refresh_interval=3h`.
- `app/news/sources/rss.py` (new): a generic RSS/Atom adapter over a
  small hardcoded list of feed URLs (e.g. the OpenAI, Anthropic, Google
  AI blogs), using the new `feedparser` dependency (handles both RSS 2.0
  and Atom robustly, unlike the hand-rolled Atom-only parser in the
  existing arXiv client), `refresh_interval=6h`.
- `app/news/registry.py` (new): `SOURCES: List[SourceAdapter]` — the
  list new sources get added to.
- `app/models/source_state.py` (new): `SourceState(source: str PK,
  last_fetched_at: Optional[datetime])` — one row per adapter. Replaces
  `AppMeta.last_news_fetch_date` (that column is left in place, unused —
  see Steps for why a hard drop isn't worth the risk).
- `app/news/service.py` (rewritten): for each registered source, check
  its `SourceState` row against its `refresh_interval`; if stale, fetch
  (same try/except-and-serve-stale-cache posture as today) and replace
  only that source's `NewsItem` rows. Aggregate all cached items across
  sources sorted by `published_date` descending, capped at a total (e.g.
  15) for the digest response.
- `app/models/news_item.py`: add `read_at: Optional[datetime] = None`.

### Backend — read tracking, streak, pet

- `app/models/engagement.py` (new): singleton `Engagement(id=1,
  current_streak: int=0, longest_streak: int=0, last_all_read_date:
  Optional[date]=None, pet_stage: int=0, pet_happiness: int=100,
  last_reminder_sent_date: Optional[date]=None)`.
- `app/engagement/service.py` (new): `recompute(session)` — lazy
  catch-up (called at the top of `GET /api/news`, same pattern as
  TASK-CARE.md's maintenance check): if `last_all_read_date` is more
  than one day before today, a day was skipped — reset
  `current_streak=0`, drop `pet_happiness` (floor 0). Also
  `mark_read(session, item_ids)` — sets `read_at`, then checks whether
  every item in today's digest is now read; if so and
  `last_all_read_date != today`, extend the streak (increment if
  yesterday, else start at 1), advance `pet_stage` at streak thresholds
  (e.g. every 3-day streak, capped), set `last_all_read_date = today`.
- `app/routers/news.py`: `GET /api/news` response becomes `{"items":
  [...], "engagement": {...}}` (bundled, not a separate endpoint — the
  panel always needs both together, and both share the same "which day
  is it" lazy-catch-up timing). Add `POST /api/news/{id}/read` and
  `POST /api/news/read-all`.

### Backend — push notifications

- New dependency: `pywebpush` (pulls in `py-vapid`, `cryptography`).
- VAPID keys generated once (`vapid --gen`, ships with `py-vapid`) and
  stored as environment variables (`VAPID_PUBLIC_KEY`,
  `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT=mailto:you@example.com`) — never
  committed; set them in the LaunchAgent plist's `EnvironmentVariables`
  dict (`backend/deploy/com.personalassistant.backend.plist`).
- `app/models/push_subscription.py` (new): `PushSubscription(id PK,
  endpoint: str unique, p256dh: str, auth: str, created_at: datetime)`.
- `app/routers/push.py` (new): `GET /api/push/public-key`, `POST
  /api/push/subscribe`, `POST /api/push/unsubscribe`.
- `app/push/service.py` (new): `send_reminder_if_needed(session)` — if
  today's digest has unread items, no reminder has been sent today
  (`Engagement.last_reminder_sent_date`), and it's past a fixed local
  hour (e.g. 18:00): `pywebpush.webpush(...)` to every
  `PushSubscription`; a `410 Gone`/expired response deletes that
  subscription row (self-cleaning, no manual pruning needed).
- `app/main.py`: on lifespan startup, `asyncio.create_task` a loop that
  wakes every ~30 minutes and calls `send_reminder_if_needed` — the one
  scheduled primitive this plan adds (see Approach §2 for why).

### Frontend

- `api/types.ts` / `api/client.ts`: `NewsItem` gains `id`, `source`,
  `read_at`; new `Engagement` type; `getNews()` returns `{items,
  engagement}`; add `markNewsRead(id)`, `markAllNewsRead()`,
  `getPushPublicKey()`, `subscribePush(sub)`, `unsubscribePush(endpoint)`.
- `components/NewsPanel.tsx`: per-item source tag (`[hn]`/`[arxiv]`/
  `[blog]`, styled like the existing `.task-tag`); clicking a link marks
  it read; a "mark all read" button; read items dim (same visual
  language as completed tasks) rather than disappearing.
- `components/PetWidget.tsx` (new): `> pet_` card — small ASCII art per
  growth stage (4–5 stages, plain text/CSS, no image assets), streak
  count, a bracket-style happiness meter (`[||||......]`, reusing the
  `[ ]`/`[x]` terminal-checkbox idiom from TODO.md).
- `src/push.ts` (new): on an explicit user tap (not an auto-prompt —
  iOS/Chrome require a gesture), request `Notification.permission`,
  `pushManager.subscribe(...)` with the VAPID public key, POST the
  subscription to the backend.
- `public/sw.js`: add a `push` event handler (`showNotification`) and a
  `notificationclick` handler (focus/open the app window).
- `index.html`: add `viewport-fit=cover` and
  `apple-mobile-web-app-status-bar-style` for a more native status-bar
  blend.
- `index.css`: `env(safe-area-inset-*)` padding on `.app-shell`,
  `overscroll-behavior-y: contain` on `body`, new `.pet-widget`/
  `.streak-meter`/`.source-tag` styles in the existing palette
  (monospace, square corners, no gradients/glow).
- Badge API: `navigator.setAppBadge(unreadCount)` /
  `navigator.clearAppBadge()` whenever the digest loads/updates —
  Home Screen icon shows an unread count on supporting platforms
  (iOS 16.4+, Chrome/Android), silently a no-op elsewhere.

### Data migration

`backend/assistant.db` gets one small, low-risk migration (back up first,
same pattern as prior plans): `ALTER TABLE newsitem ADD COLUMN read_at
DATETIME`. The new tables (`sourcestate`, `engagement`,
`pushsubscription`) are created automatically by the existing
`create_db_and_tables()` startup hook — no manual DDL. `AppMeta`'s now-
unused `last_news_fetch_date` column is left in place rather than
dropped — a no-op, zero-risk choice over a `DROP COLUMN` that buys
nothing.

## Cost & Services

| Service | Used for | Free tier | Payment trigger | Verdict |
|---|---|---|---|---|
| `pywebpush` / `py-vapid` / `cryptography` | Sending Web Push messages | Open-source Python libs, no account | Never — no service, just code | Free |
| Apple/Google/Mozilla push relays | Actually delivering the push (used implicitly by the browser Push API) | Free, no signup, no API key. Verified: Safari Web Push on an installed iOS PWA needs no Apple Developer Program account — that's a native-app-distribution requirement, not a Web Push one. | Never, at personal-use volume | Free |
| Tailscale | Reachability + HTTPS cert for the phone | Personal (free) plan: 6 users, unlimited devices, MagicDNS, `tailscale cert`/`serve` included — free tier was expanded (not shrunk) as of 2026-04. Verified via web search. | Only if you add >6 people to your tailnet | Free |
| Hacker News (Algolia API) | HN source adapter | Free, keyless, generous rate limits | Never at this polling volume | Free |
| RSS feeds (lab blogs) | Blog source adapter | Public feeds, no auth | Never | Free |
| arXiv API | Existing arXiv adapter | Free (unchanged from PARSE.md) | Never | Free |

**Bottom line: free at your scale.** Nothing here is a hosted paid
service — the two new moving parts (push relay, Tailscale certs) are
both free platform/vendor features you already qualify for.

## Steps

1. **HTTPS foundation.** If MOBILE.md's Tailscale setup isn't done yet,
   do it now (install on Mac + phone, `--host 0.0.0.0` already applied
   this session). Run `tailscale cert` for the tailnet hostname, confirm
   `https://<hostname>.ts.net:8000` loads the app on the phone with a
   valid cert. Nothing else in this plan works without this step.
2. **Multi-source backend.** Build the adapter interface + registry,
   move arXiv into it, add the Hacker News and RSS adapters, add
   `SourceState`, rewrite `service.py` for per-source lazy catch-up.
   Keep the `/api/news` response shape unchanged for now (just more/
   varied items) so nothing else breaks yet.
3. **Read tracking + streak/pet backend.** `NewsItem.read_at`,
   `Engagement` model, the recompute/mark-read logic, fold `engagement`
   into the `/api/news` response, add the read endpoints.
4. **Push backend.** Generate VAPID keys, `PushSubscription` model, the
   push router, `pywebpush` send logic, the `asyncio` reminder loop.
5. **Frontend: sources + streak/pet UI.** Source tags and mark-read/
   mark-all-read in `NewsPanel`, the new `PetWidget`.
6. **Frontend: push subscribe flow.** The permission-request button,
   `push.ts`, the `sw.js` push/notificationclick handlers, Badge API
   calls.
7. **Native-feel polish.** Safe-area CSS, status-bar meta, overscroll
   containment.
8. **End-to-end verification on the real phone** (see below), deploy via
   `backend/deploy/reload.sh`, confirm the LaunchAgent plist carries the
   new `EnvironmentVariables` (VAPID keys) after reload.

## Out of Scope

- **Auth / per-user push targeting.** Still a single-user app with no
  login (MOBILE.md's security note still applies unchanged) — one shared
  set of push subscriptions, one shared streak.
- **A source-management UI.** Sources are a developer-maintained list in
  `registry.py` for now, not a settings screen with toggles.
- **A native app wrapper** (Capacitor/React Native) — superseded by
  "keep extending the PWA," per Approach §4.
- **Task-completion streaks.** This plan's streak is specifically about
  reading the news digest, not completing to-dos — TASK-CARE.md's task
  lifecycles are a separate, unrelated concern.
- **Rich pet mechanics** — no feeding minigame, no multiple pets, no
  cosmetics or store. One pet, driven purely by the streak.
- **Push delivery guarantees.** Best-effort, single attempt per
  reminder tick; a dead subscription is quietly dropped, not retried.
- **Cross-source deduplication** (e.g. the same paper surfacing via
  arXiv and an RSS aggregator) — not handled.
