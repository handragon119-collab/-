# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
calendar_access.py — read Apple Calendar via AppleScript.

Read-only by design. Events for "today" / "upcoming" are pulled through
osascript and cached in-memory for a short TTL, with a background thread
refreshing the cache so voice responses stay snappy (AppleScript calendar
queries can be slow on the first hit).
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any

from applescript import available, run_safe

_CACHE_TTL = 120.0  # seconds
_cache: dict[str, Any] = {"events": [], "fetched": 0.0}
_lock = threading.Lock()


def _accounts_filter() -> list[str]:
    raw = os.environ.get("CALENDAR_ACCOUNTS", "").strip()
    return [a.strip() for a in raw.split(",") if a.strip()]


# AppleScript: list today's events as "start|||end|||title" lines.
_TODAY_SCRIPT = '''
set output to ""
set today to current date
set startOfDay to today - (time of today)
set endOfDay to startOfDay + (24 * 60 * 60)
tell application "Calendar"
  repeat with c in calendars
    set evs to (every event of c whose start date >= startOfDay and start date < endOfDay)
    repeat with e in evs
      set output to output & (start date of e as string) & "|||" & (summary of e) & linefeed
    end repeat
  end repeat
end tell
return output
'''


def _parse(raw: str) -> list[dict[str, str]]:
    events = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or "|||" not in line:
            continue
        start, _, title = line.partition("|||")
        events.append({"start": start.strip(), "title": title.strip()})
    return events


def _fetch() -> list[dict[str, str]]:
    if not available():
        return []
    raw = run_safe(_TODAY_SCRIPT, fallback="", timeout=20.0)
    return _parse(raw)


def today(force: bool = False) -> list[dict[str, str]]:
    """Return today's events, served from cache when fresh."""
    with _lock:
        fresh = (time.time() - _cache["fetched"]) < _CACHE_TTL
        if _cache["events"] and fresh and not force:
            return list(_cache["events"])
    events = _fetch()
    with _lock:
        _cache["events"] = events
        _cache["fetched"] = time.time()
    return events


def summary_line() -> str:
    """A short spoken-friendly summary of today's calendar."""
    events = today()
    if not available():
        return "Calendar access is only available on macOS, sir."
    if not events:
        return "Your calendar is clear for the rest of today."
    parts = [f"{e['title']} at {e['start']}" for e in events[:4]]
    return "You have " + "; ".join(parts) + "."


def start_background_refresh(interval: float = _CACHE_TTL) -> None:
    """Spawn a daemon thread that keeps the cache warm."""
    if not available():
        return

    def _loop() -> None:
        while True:
            today(force=True)
            time.sleep(interval)

    threading.Thread(target=_loop, daemon=True, name="calendar-refresh").start()


if __name__ == "__main__":
    print(summary_line())
