# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
actions.py — system actions JARVIS can take on macOS.

Thin AppleScript / shell wrappers: open apps, open URLs in Chrome, run a
command in a new Terminal window. These are the "do something on my Mac"
verbs the LLM can trigger via [ACTION:...] tags.
"""

from __future__ import annotations

import shutil
import subprocess

from applescript import available, run_safe


def open_app(name: str) -> bool:
    if not available():
        return False
    safe = name.replace('"', "")
    out = run_safe(f'tell application "{safe}" to activate\nreturn "ok"', fallback="")
    return out.strip() == "ok"


def open_url(url: str) -> bool:
    """Open a URL in Google Chrome (the browser JARVIS' frontend targets)."""
    if not available():
        return False
    safe = url.replace('"', "")
    script = f'''
    tell application "Google Chrome"
      activate
      open location "{safe}"
    end tell
    return "ok"
    '''
    return run_safe(script, fallback="").strip() == "ok"


def open_terminal(command: str = "") -> bool:
    """Open Terminal, optionally running a command."""
    if not available():
        return False
    safe = command.replace('"', '\\"')
    if safe:
        script = f'tell application "Terminal" to do script "{safe}"\nreturn "ok"'
    else:
        script = 'tell application "Terminal" to activate\nreturn "ok"'
    return run_safe(script, fallback="").strip() == "ok"


def run_shell(command: str, timeout: float = 30.0) -> str:
    """Run a shell command and capture output (used for local utilities)."""
    try:
        proc = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return (proc.stdout + proc.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"(command timed out after {timeout}s)"


def has(binary: str) -> bool:
    return shutil.which(binary) is not None
