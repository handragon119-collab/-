# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
applescript.py — thin, safe wrapper around macOS `osascript`.

Every macOS integration (Calendar, Mail, Notes, system actions) ultimately
shells out to AppleScript through here. Centralising it means:
  * one place to enforce a timeout
  * graceful, predictable behaviour when *not* on macOS (so the rest of the
    app — and CI on Linux — can import and run without exploding)
"""

from __future__ import annotations

import platform
import subprocess

IS_MACOS = platform.system() == "Darwin"


class AppleScriptError(RuntimeError):
    pass


def available() -> bool:
    return IS_MACOS


def run(script: str, timeout: float = 15.0) -> str:
    """Run an AppleScript snippet and return its stdout (stripped).

    On non-macOS platforms this raises AppleScriptError so callers can fall
    back to a friendly "not available here" response rather than crashing.
    """
    if not IS_MACOS:
        raise AppleScriptError("AppleScript is only available on macOS")
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - timing
        raise AppleScriptError(f"AppleScript timed out after {timeout}s") from exc
    if proc.returncode != 0:
        raise AppleScriptError(proc.stderr.strip() or "AppleScript failed")
    return proc.stdout.strip()


def run_safe(script: str, fallback: str = "", timeout: float = 15.0) -> str:
    """Like run() but never raises — returns `fallback` on any error."""
    try:
        return run(script, timeout=timeout)
    except AppleScriptError:
        return fallback
