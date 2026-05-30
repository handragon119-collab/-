# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
notes_access.py — Apple Notes integration via AppleScript.

Read existing notes and create new ones. Editing and deleting are deliberately
unsupported so JARVIS can never clobber the user's existing notes.
"""

from __future__ import annotations

from typing import Any

from applescript import available, run_safe

_LIST_SCRIPT = '''
set output to ""
tell application "Notes"
  set theNotes to notes
  set n to 0
  repeat with nt in theNotes
    set output to output & (name of nt) & linefeed
    set n to n + 1
    if n >= %d then exit repeat
  end repeat
end tell
return output
'''

_READ_SCRIPT = '''
tell application "Notes"
  set matches to (notes whose name contains "%s")
  if (count of matches) is 0 then return ""
  set theNote to item 1 of matches
  return (body of theNote) as string
end tell
'''

_CREATE_SCRIPT = '''
tell application "Notes"
  tell account 1
    make new note at folder "Notes" with properties {name:"%s", body:"%s"}
  end tell
end tell
return "ok"
'''


def list_titles(limit: int = 10) -> list[str]:
    if not available():
        return []
    raw = run_safe(_LIST_SCRIPT % max(1, limit), fallback="", timeout=20.0)
    return [l.strip() for l in raw.splitlines() if l.strip()]


def read(title: str) -> str:
    if not available():
        return ""
    safe = title.replace('"', "")
    return run_safe(_READ_SCRIPT % safe, fallback="", timeout=20.0)


def create(title: str, body: str) -> bool:
    if not available():
        return False
    safe_title = title.replace('"', "'")
    # Notes bodies are HTML; wrap plain text in a <div> and escape quotes.
    safe_body = body.replace('"', "'").replace("\n", "<br>")
    result = run_safe(_CREATE_SCRIPT % (safe_title, safe_body), fallback="", timeout=20.0)
    return result.strip() == "ok"


if __name__ == "__main__":
    print(list_titles())
