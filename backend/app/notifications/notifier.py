"""macOS notification helper via osascript (never shell=True)."""

from __future__ import annotations

import subprocess


def _escape(s: str) -> str:
    """Escape backslashes and double quotes for an AppleScript string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def notify(title: str, message: str) -> None:
    """Display a macOS notification. Best-effort; never raises."""
    safe_title = _escape(title)
    safe_message = _escape(message)
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except Exception:
        # Notifications are best-effort; failure must never break the app.
        pass
