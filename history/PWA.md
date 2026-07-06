# PWA.md implementation summary

Implemented 2026-07-06, from `plans/PWA.md`: single-process serving (backend
serves the built frontend), PWA installability, and a LaunchAgent template
for always-on background operation.

## What changed

### One process
- `backend/app/main.py`: mounts `StaticFiles(directory=frontend/dist,
  html=True)` at `/`, added after the `/api` routers so it can't shadow
  them. The mount is guarded by an `is_dir()` check so plain `uvicorn`
  still starts in a fresh checkout before any `npm run build` (dev keeps
  using the Vite proxy, untouched). FastAPI title updated to
  "Personal To-Do Assistant" while there.

### PWA
- `frontend/public/manifest.webmanifest` (new): standalone display,
  `start_url`/`scope` at `/`, background/theme color `#0a0d0a` (terminal
  dark palette), 192 + 512 icons with the 512 marked `any maskable`.
- Icons: the old `favicon.svg`/`icons.svg` were off-brand purple
  gradient-blur placeholders, so instead of rasterizing them a new flat
  terminal-style `>_` mark was drawn (`public/icons/icon.svg`, pure paths,
  palette colors) and rasterized with `qlmanage`/`sips` (no new deps) to
  `icon-192.png`/`icon-512.png`. Old placeholder SVGs deleted.
- `frontend/index.html`: manifest link, `theme-color` meta, Safari
  Add-to-Dock tags (`apple-mobile-web-app-capable`/`-title`,
  `apple-touch-icon`), icon link updated, and the stale
  "Scheduling Assistant" title fixed to `to-do_`.
- `frontend/public/sw.js` (new): pass-through service worker with no fetch
  handler — exists only for Chrome's installability check. Registered from
  `main.tsx` behind `import.meta.env.PROD` (an addition to the plan: keeps
  dev serving from ever fighting a registered worker) plus the
  `'serviceWorker' in navigator` guard.

### LaunchAgent
- `backend/deploy/com.personalassistant.backend.plist` (new template):
  uvicorn on :8000, `RunAtLoad` + `KeepAlive`, logs to
  `~/Library/Logs/personal-assistant/`. Absolute paths left as
  `/ABSOLUTE/PATH/TO/...`/`YOUR_USERNAME` placeholders per the plan.
- README: new "Run it as a background app (PWA + LaunchAgent)" section —
  fill-in-and-bootstrap instructions, the bootout/bootstrap + rebuild cycle
  for code updates, and Safari/Chrome install steps.

## Deviations / notes
- **No SPA fallback for unknown paths.** The plan assumed
  `StaticFiles(html=True)` serves `index.html` for any non-API path; it
  actually only serves directory indexes, so `/nonexistent` returns 404.
  Left as-is deliberately: after TODO.md the app has no client-side routes
  (single page, `start_url: "/"`), so a catch-all would be dead machinery.
  If routes ever return, add an explicit index.html fallback then.
- Executed directly (no subagent delegation) — small, tightly coupled
  config/static work where handoff overhead would exceed the savings.

## Verification
- `npm run build` clean; `uvicorn` on a test port then:
  `/` returns the built `index.html` (200), `/manifest.webmanifest` parses
  as valid JSON with both icons, `/sw.js` serves as `text/javascript`,
  both PNGs serve as `image/png`, and `/api/health` + `/api/tasks` still
  work alongside the static mount.
- Icon PNGs verified visually (flat near-black + phosphor-green `>_`,
  glyph inside the maskable safe zone) and dimensionally (512/192).
- Not verified here (needs GUI): DevTools manifest/SW panel, the actual
  Safari "Add to Dock" / Chrome "Install" flows, and loading the
  LaunchAgent — the plist is a template; bootstrap it per the README.
