# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
mail_access.py — read-only Apple Mail access via AppleScript.

JARVIS can report the unread count, read out recent messages, and search the
inbox. It never sends, deletes, or modifies mail — by design.
"""

from __future__ import annotations

from typing import Any

from applescript import available, run_safe

_UNREAD_SCRIPT = '''
tell application "Mail"
  return unread count of inbox
end tell
'''

_RECENT_SCRIPT = '''
set output to ""
tell application "Mail"
  set msgs to messages 1 thru %d of inbox
  repeat with m in msgs
    set output to output & (sender of m) & "|||" & (subject of m) & linefeed
  end repeat
end tell
return output
'''

_SEARCH_SCRIPT = '''
set output to ""
tell application "Mail"
  set msgs to (messages of inbox whose subject contains "%s")
  set n to 0
  repeat with m in msgs
    set output to output & (sender of m) & "|||" & (subject of m) & linefeed
    set n to n + 1
    if n >= %d then exit repeat
  end repeat
end tell
return output
'''


def _parse(raw: str) -> list[dict[str, str]]:
    out = []
    for line in raw.splitlines():
        if "|||" not in line:
            continue
        sender, _, subject = line.partition("|||")
        out.append({"from": sender.strip(), "subject": subject.strip()})
    return out


def unread_count() -> int:
    if not available():
        return 0
    raw = run_safe(_UNREAD_SCRIPT, fallback="0", timeout=15.0)
    try:
        return int(raw.strip() or 0)
    except ValueError:
        return 0


def recent(limit: int = 5) -> list[dict[str, str]]:
    if not available():
        return []
    raw = run_safe(_RECENT_SCRIPT % max(1, limit), fallback="", timeout=20.0)
    return _parse(raw)


def search(term: str, limit: int = 5) -> list[dict[str, str]]:
    if not available():
        return []
    safe = term.replace('"', "")
    raw = run_safe(_SEARCH_SCRIPT % (safe, max(1, limit)), fallback="", timeout=20.0)
    return _parse(raw)


def summary_line() -> str:
    if not available():
        return "Mail access is only available on macOS, sir."
    n = unread_count()
    if n == 0:
        return "Your inbox is all caught up — no unread mail."
    msgs = recent(3)
    heads = "; ".join(f"{m['subject']} from {m['from']}" for m in msgs)
    return f"You have {n} unread message{'s' if n != 1 else ''}. Most recent: {heads}."


if __name__ == "__main__":
    print(summary_line())
