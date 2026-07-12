# ENGAGE.md implementation summary

Implemented 2026-07-06, from `plans/ENGAGE.md`: multi-source news digest,
read-streak + pet, Web Push reminders, and native-feel PWA polish.

## What changed

### Multi-source digest
- `app/news/sources/` (new): `base.py` adapter interface (`name`,
  `refresh_interval`, `async fetch()`); `arxiv.py` (moved from the old
  `arxiv_client.py`, 24h cadence); `hackernews.py` (Algolia HN front-page
  API, keyless, 3h cadence, "N points, M comments" as summary);
  `rss.py` (feedparser over three AI feeds, 6h cadence, HTML stripped
  from summaries before truncation).
  - **Feed-choice deviation:** instead of the plan's example lab blogs
    (OpenAI/Anthropic/Google), whose RSS URLs churn, the adapter uses
    MIT Technology Review / The Verge / Ars Technica AI-topic feeds —
    stable URL patterns, individually failure-isolated.
- `app/news/registry.py`: the `SOURCES` list new adapters get added to.
- `SourceState` table (new): per-source `last_fetched_at` — replaces
  `AppMeta.last_news_fetch_date` (column left in place, unused).
- `app/news/service.py` rewritten: per-source staleness check + fetch
  with the existing serve-stale-on-failure posture, one source failing
  never blanks the rest; aggregate sorted by `published_date` desc,
  capped at 15.

### Read tracking, streak, pet
- `NewsItem.read_at` (migration applied to `assistant.db`, backed up
  first). `Engagement` singleton table: streak, longest, pet stage
  (0–4, +1 per 3 streak days), happiness (skip a day → −20, floor 0;
  streak resets on a skipped day but longest is kept).
- `app/engagement/service.py`: lazy `recompute()` on every digest read;
  `mark_read()` extends the streak the first time all cached items are
  read on a given day.
- `GET /api/news` now returns `{items, engagement}`; new
  `POST /api/news/{id}/read` and `POST /api/news/read-all`.

### Web Push
- `pywebpush` + `PushSubscription` table + `/api/push/public-key`,
  `/subscribe`, `/unsubscribe` (upsert/idempotent).
- `app/push/service.py::send_reminder_if_needed`: after 18:00 local, if
  today's digest has unread items and no reminder was sent today, push
  to every subscription; 404/410 responses self-delete the subscription.
  Strict no-op when VAPID env vars are absent.
- `app/main.py`: 30-minute `asyncio` reminder loop in the lifespan (the
  one deliberate exception to the no-scheduler rule — see the plan's
  Approach §2), cancelled on shutdown.
- VAPID keys generated to `~/.personal-assistant/vapid/` (outside the
  repo, never committed; `.gitignore` hardened anyway). Real values live
  only in the installed `~/Library/LaunchAgents/...plist`
  (`EnvironmentVariables`); the repo template carries `FILL_ME_IN`
  placeholders + how-to comment.

### Frontend
- `NewsPanel` rewritten: `[source]` tags, click-to-mark-read links,
  "mark all read", read items dimmed; Badging API mirrors the unread
  count onto the installed app icon (no-op where unsupported).
- `PetWidget` (new): 5-stage ASCII pet, streak line, `[||||......]`
  happiness meter, and the "enable notifications" button (explicit
  gesture, as iOS/Chrome require) with inline status.
- `push.ts` (new): permission → SW registration → `pushManager.subscribe`
  with the VAPID key → POST to backend; returns false, never throws.
- `sw.js`: `push` (showNotification) + `notificationclick`
  (focus/open) handlers.
- Native-feel: `viewport-fit=cover`, `black-translucent` status bar,
  safe-area insets on `.app-shell`, `overscroll-behavior-y: contain`.
- Sidebar restructured: `.sidebar` column (PetWidget + NewsPanel),
  stacks under 900px.

## Build notes
- Backend agent stalled twice mid-run (harness timeouts, not code
  issues); resumed from its own transcript once and its final gates were
  re-verified independently after the second cutoff.
- Smoke-test read-marks and streak credit were reset in the production
  DB afterward — engagement starts clean at 0.

## Verification
- 20/20 backend tests; clean `npm run build`; clean import with no
  VAPID env (push disabled path).
- Test-port e2e: all three sources fetched live (5+5+5, capped 15),
  mark-one-read → `read_at` set, read-all → streak 1 / longest 1,
  public-key served, subscribe 200 / unsubscribe 204.
- Deployed via `reload.sh`; live :8000 serves 15 items + engagement and
  a non-empty push public key from the LaunchAgent env.

## Remaining manual steps (can't be done from the CLI)
1. **Tailscale + HTTPS (plan Step 1)** — Tailscale is not installed yet.
   Install it on Mac + phone, sign in, enable MagicDNS, then
   `tailscale cert` — required before the *phone* can subscribe to push
   (Web Push needs a secure context; plain `http://10.x.x.x:8000` won't
   allow it). Desktop push already works today via `http://localhost:8000`
   (localhost counts as secure).
2. On each device, tap **enable notifications** in the pet card once.
3. Reminder fires after 18:00 local when unread items exist — to test
   eagerly, temporarily lower `REMINDER_HOUR` in `app/push/service.py`.
