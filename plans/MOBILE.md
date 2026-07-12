# Mobile access via Tailscale — no separate mobile app

## Context

The user wants to use this app from their phone with the desktop and
mobile kept in sync. Because the app is already a PWA (PWA.md) talking to
a single REST API + SQLite database (no per-device data), there's no
separate mobile codebase to build and no sync protocol to write — "sync"
is just "both devices talk to the same backend." The only real gap is
that the backend is currently only reachable from the Mac itself
(uvicorn binds to loopback by default), so a phone on the same Wi-Fi, let
alone off it, can't reach it at all.

Tailscale (free tier: up to 3 users / 100 devices, plenty for a personal
setup) solves the reachability problem without exposing the app to the
public internet — which matters here because **the app currently has no
authentication**. A private tailnet means only your own signed-in
devices can ever reach it; the app doesn't need to grow a login system
just to be reachable from your phone.

## What changes, and what doesn't

- **No new mobile app.** The existing PWA installs on the phone exactly
  as it does on the Mac (Safari → **Add to Home Screen**), pointed at the
  same backend.
- **No sync code.** One SQLite DB, one FastAPI backend, two clients. A
  task checked off on the phone shows checked off on the Mac on next
  fetch, because it's the same row in the same database — nothing to
  build here beyond making the backend reachable.
- **What does change**: the backend needs to accept connections from
  outside `localhost`, and the phone needs a stable address to reach it
  at over the tailnet.

## Setup

1. **Install Tailscale on the Mac** (`brew install --cask tailscale` or
   the App Store app) and sign in.
2. **Install Tailscale on the phone** (App Store / Play Store), sign in
   with the same account — this puts both devices on one private tailnet.
3. **Enable MagicDNS** in the Tailscale admin console, so the Mac gets a
   stable hostname (e.g. `mac-mini.tailXXXX.ts.net`) instead of a bare
   IP that could change.
4. **Bind uvicorn to all interfaces, not just loopback.** Today's
   `backend/deploy/com.personalassistant.backend.plist` runs
   `uvicorn app.main:app --port 8000` with no `--host`, which defaults to
   `127.0.0.1` — unreachable from anywhere but the Mac. Add
   `--host 0.0.0.0` to `ProgramArguments`. (Tailscale itself is the
   security boundary here, not the bind address — nothing outside the
   tailnet can route to the Mac unless the router is also port-forwarded,
   which this setup doesn't need or want.)
5. **macOS Firewall prompt**: the first time uvicorn listens on all
   interfaces, System Settings → Network → Firewall may ask whether to
   allow incoming connections for `uvicorn`/`python` — allow it.
6. **CORS needs no change.** The backend already serves the built
   frontend itself (`app/main.py` mounts `frontend/dist` at `/`), so
   loading `http://mac-mini.tailXXXX.ts.net:8000` gives you the frontend
   and API from the same origin — CORS only exists today for the
   `vite dev` proxy case and isn't in play here.
7. **On the phone**: open `http://mac-mini.tailXXXX.ts.net:8000` in
   Safari, confirm the to-do list and news panel load, then **Add to
   Home Screen**.
8. **On the Mac**: no change needed — keep using `localhost:8000` there,
   since it's faster and doesn't depend on Tailscale being up locally.
   Both hostnames reach the identical database, so there's no reason to
   make the Mac's own access path depend on the tailnet too.

## Known limitation: service worker over plain HTTP

`frontend/public/sw.js` (from PWA.md) only registers in a "secure
context" — HTTPS, or the special-cased `http://localhost`. Reached over
`http://mac-mini.tailXXXX.ts.net:8000` (plain HTTP, not localhost), the
service worker won't register. This doesn't block anything on iOS
Safari — "Add to Home Screen" there doesn't require a service worker at
all — but it would matter for a Chrome/Android install later, where the
install prompt depends on one being registered.

- **Follow-up if that's ever needed**: `tailscale serve` can terminate
  HTTPS for you using Tailscale's own certificate integration
  (`tailscale cert`), giving the tailnet hostname a real TLS cert with no
  extra reverse proxy to run. Out of scope for the initial phone-via-
  Safari setup, worth a line in the README as a "if you want this on
  Android too" note.
  - **Update: no longer optional.** `plans/ENGAGE.md` (push
    notifications) needs a real secure context to subscribe to Web Push
    from the phone — plain HTTP won't do, even on iOS Safari. That plan's
    Step 1 promotes this follow-up to a hard prerequisite: finish the
    Tailscale setup above, then run `tailscale cert` before attempting
    the push-notification pieces.

## Security note (belongs in the README)

- The app has no login/auth of any kind. Safe *only* because reachability
  is gated by your private tailnet membership — anyone you ever invite
  onto that tailnet (or a future public exposure via port-forwarding or
  a tunnel) would be able to read/edit the to-do list and trigger the
  arXiv fetch with zero restriction. Don't port-forward this or put it
  behind a public tunnel without adding auth first.

## Verification

- From the phone, on cellular data (Wi-Fi off), confirm
  `http://mac-mini.tailXXXX.ts.net:8000` loads the app — proves it's
  actually working over the tailnet and not just LAN.
- Add a task on the phone, refresh the Mac's tab, confirm it appears
  (and vice versa) — proves the "sync" is just shared-backend behavior.
- Confirm the arXiv news panel loads identically on both.
- Restart the Mac (or `launchctl kickstart`) and confirm the phone can
  still reach it afterward — proves the `--host 0.0.0.0` change survived
  in the LaunchAgent plist, not just a one-off manual run.
