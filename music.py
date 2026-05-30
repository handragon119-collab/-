"""
music.py - 깨어날 때 트는 음악 (AC/DC - Back in Black).

저작권 때문에 음원 파일은 저장소에 포함하지 않습니다.
1) 로컬에 음원 파일이 있으면 그걸 재생하고,
2) 없으면 유튜브에서 'Back in Black'을 열어줍니다.

로컬 파일 지정 방법:
  - .env 에  JARVIS_WAKE_MUSIC=/경로/back_in_black.mp3
  - 또는 assets/back_in_black.mp3 에 파일을 두면 자동 인식
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import webbrowser

# AC/DC - Back in Black 공식 영상 검색 결과
BACK_IN_BLACK_YT = (
    "https://www.youtube.com/results?search_query=AC%2FDC+Back+in+Black+official"
)

_CANDIDATES = ["assets/back_in_black.mp3", "back_in_black.mp3"]


def play_wake_music():
    """깨어날 때 음악을 (가능하면 백그라운드로) 재생한다."""
    path = (os.getenv("JARVIS_WAKE_MUSIC") or "").strip()
    if not path:
        for c in _CANDIDATES:
            if os.path.exists(c):
                path = c
                break

    if path and os.path.exists(path):
        return _play_file(path)

    # 로컬 음원이 없으면 유튜브로 대체
    print("🎵 로컬 음원이 없어 유튜브에서 'Back in Black'을 엽니다.")
    try:
        webbrowser.open(BACK_IN_BLACK_YT)
    except Exception:
        pass
    return None


def _play_file(path: str):
    """OS별 기본 플레이어로 음원 파일을 백그라운드 재생."""
    system = platform.system()
    print(f"🎸 Back in Black 재생: {path}")
    try:
        if system == "Darwin":                       # macOS
            return subprocess.Popen(["afplay", path])
        if system == "Windows":
            os.startfile(path)                        # type: ignore[attr-defined]
            return None
        # Linux: 설치된 플레이어를 순서대로 시도
        players = {
            "ffplay": ["ffplay", "-nodisp", "-autoexit", path],
            "mpg123": ["mpg123", "-q", path],
            "mpv":    ["mpv", "--no-video", path],
            "cvlc":   ["cvlc", "--play-and-exit", path],
            "paplay": ["paplay", path],
            "aplay":  ["aplay", path],
        }
        for name, cmd in players.items():
            if shutil.which(name):
                return subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        subprocess.Popen(["xdg-open", path])          # 최후의 수단
    except Exception as exc:
        print(f"[music] 재생 실패: {exc}")
    return None
