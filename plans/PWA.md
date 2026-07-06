# Always-on background access: PWA + LaunchAgent

## Context

The app currently needs two terminals running (`uvicorn` + `vite dev`) to
be reachable at all, and closing them kills it. The user wants this to be
a background service that's always up and reachable like a normal Mac
app, without building a native wrapper. The two pieces: (1) the backend
runs unattended, starts on login, and restarts itself if it crashes; (2)
the frontend installs as a PWA (Dock icon, its own window, no browser
chrome/tabs) instead of living in a bookmarked tab.

This intentionally stops short of the menu-bar-app route discussed
earlier — that requires a native shell (e.g. Tauri) and is real new code
to build and maintain. This plan is the "working in the next session"
option: no new runtime dependencies, just config + a couple of static
files.

## One process, not two

Today `vite dev` (port 5174) proxies `/api` to `uvicorn` (port 8000) —
fine for development, but it's an extra thing that has to be running for
the app to work. For an always-on setup, the backend should serve the
already-built frontend directly, so there's exactly one process:

- `frontend/`: `npm run build` emits static files to `frontend/dist/`
  (already the default Vite output dir — no vite.config.ts change
  needed).
- `backend/app/main.py`: after the `/api` routers are registered, mount
  `StaticFiles(directory=<repo>/frontend/dist, html=True)` at `/`, so any
  non-API path serves `index.html` (client-side routing, if any survives
  the scheduler-removal plan, still works on refresh). Route order matters
  — the catch-all static mount must be added *after* the API routers.
- `npm run dev` / the Vite proxy setup stays untouched for active
  development; this only matters for the "always running" deployment.

## PWA installability

- `frontend/public/manifest.webmanifest` (new): `name`, `short_name`,
  `start_url: "/"`, `scope: "/"`, `display: "standalone"`, `theme_color`
  and `background_color` matching the terminal palette from TODO.md, and
  `icons` entries (192×192 and 512×512 PNG, plus a maskable 512×512 for
  Android/Chrome — not load-bearing on macOS but cheap to include).
- Icons: `favicon.svg`/`icons.svg` already exist but are placeholder SVGs,
  not the sized PNGs a manifest needs. Rasterize once (e.g. `sips` or
  `rsvg-convert`, both scriptable, no new npm dependency) into
  `frontend/public/icons/icon-192.png` and `icon-512.png`.
- `frontend/index.html`: add `<link rel="manifest" href="/manifest.webmanifest">`,
  a `<meta name="theme-color">`, and the Safari-specific tags
  (`apple-mobile-web-app-capable`, `apple-mobile-web-app-title`,
  `apple-touch-icon`) so "Add to Dock" picks up the right name/icon.
- Minimal service worker (`frontend/public/sw.js`, new): register it from
  `main.tsx` behind `if ('serviceWorker' in navigator)`. This app is
  fundamentally not offline-capable (it's a live local API, not cached
  data), so the worker does nothing but pass requests through — no
  offline cache, no `vite-plugin-pwa` dependency. Its only job is to
  satisfy Chrome's installability check; Safari's "Add to Dock" doesn't
  require one at all.

## Backend as a background service (LaunchAgent)

- Add a plist template to the repo, e.g.
  `backend/deploy/com.personalassistant.backend.plist`, with
  `ProgramArguments` pointing at `backend/.venv/bin/uvicorn app.main:app
  --port 8000`, `WorkingDirectory` set to the repo's `backend/` path,
  `RunAtLoad` and `KeepAlive` both `true` (auto-start on login, restart on
  crash), and `StandardOutPath`/`StandardErrorPath` pointing at
  `~/Library/Logs/personal-assistant/`. Keep the absolute paths as a
  placeholder the README tells you to fill in (they're machine-specific,
  so this file is a template, not something `launchctl` reads directly
  from the repo).
- README addition: copy the filled-in plist to
  `~/Library/LaunchAgents/`, then
  `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.personalassistant.backend.plist`
  to start it, and how to unload/reload after pulling code changes
  (`launchctl bootout` + `bootstrap` again, plus re-running
  `npm run build` since the backend serves whatever is currently in
  `frontend/dist/`).

## Install steps (after both pieces are in place)

1. `cd frontend && npm run build`.
2. Load the LaunchAgent (or just run uvicorn manually once to test).
3. Open `http://localhost:8000` in Safari or Chrome.
4. Safari: **File → Add to Dock**. Chrome: address-bar install icon →
   **Install**. Either way you get a standalone window + Dock icon,
   backed by the always-running LaunchAgent service.

## Verification

- `cd frontend && npm run build && cd ../backend && .venv/bin/uvicorn app.main:app --port 8000`
  — confirm `http://localhost:8000` serves the app (not a 404/CORS error),
  and `http://localhost:8000/manifest.webmanifest` returns valid JSON.
- DevTools → Application tab: manifest recognized, service worker
  registered with no errors.
- Install as a PWA in both Safari and Chrome; confirm the Dock icon,
  window title, and standalone chrome (no address bar) look right.
- Load the LaunchAgent, reboot (or `launchctl kickstart -k`), confirm the
  server comes back up with no Terminal window open, and check the log
  files under `~/Library/Logs/personal-assistant/` for a clean start.
