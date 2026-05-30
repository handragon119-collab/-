# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
work_mode.py — long-running background tasks via persistent Claude Code sessions.

When the user asks JARVIS to "build", "research", or otherwise do real work,
we hand it to a headless Claude Code process (`claude -p --continue`) running
in a project directory. Output is streamed to a file the frontend can poll,
and the session is resumable across turns via --continue.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

OUTPUT_FILE = Path("data/.jarvis_output.txt")
SESSION_FILE = Path("data/active_session.json")


class WorkSession:
    def __init__(self, workdir: str | None = None) -> None:
        self.workdir = workdir or os.getcwd()
        self.proc: subprocess.Popen | None = None
        self.running = False
        self.started = 0.0
        self.last_prompt = ""

    def _claude_available(self) -> bool:
        from shutil import which
        return which("claude") is not None

    def run(self, prompt: str) -> dict[str, Any]:
        """Kick off (or continue) a background Claude Code task."""
        if not self._claude_available():
            return {"ok": False, "error": "claude CLI not found on PATH"}
        if self.running:
            return {"ok": False, "error": "a work session is already running"}

        self.last_prompt = prompt
        self.started = time.time()
        self.running = True
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text("")

        def _worker() -> None:
            try:
                with OUTPUT_FILE.open("w") as out:
                    self.proc = subprocess.Popen(
                        ["claude", "-p", "--continue", prompt],
                        cwd=self.workdir,
                        stdout=out,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                    self.proc.wait()
            finally:
                self.running = False

        threading.Thread(target=_worker, daemon=True, name="work-mode").start()
        return {"ok": True, "message": "Work session started"}

    def status(self) -> dict[str, Any]:
        tail = ""
        if OUTPUT_FILE.exists():
            content = OUTPUT_FILE.read_text(errors="ignore")
            tail = content[-2000:]
        return {
            "running": self.running,
            "elapsed": round(time.time() - self.started, 1) if self.started else 0,
            "prompt": self.last_prompt,
            "output_tail": tail,
        }

    def stop(self) -> bool:
        if self.proc and self.running:
            self.proc.terminate()
            self.running = False
            return True
        return False


_default: WorkSession | None = None


def get_work_session() -> WorkSession:
    global _default
    if _default is None:
        _default = WorkSession()
    return _default
