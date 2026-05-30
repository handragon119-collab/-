"""
commands.py - 자비스의 손발(기본 명령어).

LLM에 보내기 전에, 빠르고 정확해야 하는 동작들은 여기서 직접 처리한다.
유튜브 튜토리얼의 '하드코딩 명령어'에 해당하는 부분이다.
처리하면 (응답문자열)을, 해당 명령이 아니면 None을 반환한다.
"""
from __future__ import annotations

import datetime
import os
import platform
import subprocess
import webbrowser
from urllib.parse import quote


def _open_url(url: str) -> None:
    webbrowser.open(url)


def _open_app(app: str) -> bool:
    """OS별로 앱을 연다. 성공하면 True."""
    system = platform.system()
    try:
        if system == "Darwin":      # macOS
            subprocess.Popen(["open", "-a", app])
        elif system == "Windows":
            os.startfile(app)  # type: ignore[attr-defined]
        else:                        # Linux
            subprocess.Popen([app.lower()])
        return True
    except Exception:
        return False


def handle(text: str) -> str | None:
    """명령어 라우팅. 처리했으면 응답 문자열, 아니면 None."""
    t = text.lower().strip()
    if not t:
        return None

    # 1) 시간 / 날짜
    if any(k in t for k in ["몇 시", "몇시", "시간", "time", "지금 몇"]):
        now = datetime.datetime.now()
        return f"지금은 {now.hour}시 {now.minute}분입니다."
    if any(k in t for k in ["며칠", "날짜", "오늘 무슨", "date", "오늘 며"]):
        now = datetime.datetime.now()
        days = ["월", "화", "수", "목", "금", "토", "일"]
        return f"오늘은 {now.year}년 {now.month}월 {now.day}일 {days[now.weekday()]}요일입니다."

    # 2) 웹 검색 (유튜브 / 일반)
    if "유튜브" in t or "youtube" in t:
        q = _strip_keywords(text, ["유튜브", "youtube", "에서", "검색", "틀어", "찾아", "줘"])
        if q:
            _open_url(f"https://www.youtube.com/results?search_query={quote(q)}")
            return f"유튜브에서 '{q}'를 검색했습니다."
        _open_url("https://www.youtube.com")
        return "유튜브를 열었습니다."

    if any(k in t for k in ["검색", "찾아", "search", "구글"]):
        q = _strip_keywords(text, ["구글", "google", "에서", "검색", "찾아", "해줘", "줘", "좀"])
        if q:
            _open_url(f"https://www.google.com/search?q={quote(q)}")
            return f"'{q}'에 대해 검색했습니다."

    # 3) 앱/사이트 열기
    if "열어" in t or "open" in t or "켜줘" in t:
        sites = {
            "깃허브": "https://github.com", "github": "https://github.com",
            "네이버": "https://www.naver.com", "naver": "https://www.naver.com",
            "유튜브": "https://www.youtube.com", "구글": "https://www.google.com",
            "메일": "https://mail.google.com", "지메일": "https://mail.google.com",
        }
        for name, url in sites.items():
            if name in t:
                _open_url(url)
                return f"{name}를 열었습니다."

    # 4) 인사 / 정체성
    if any(k in t for k in ["안녕", "hello", "hi", "반가워"]):
        return "안녕하세요. 무엇을 도와드릴까요?"
    if any(k in t for k in ["누구", "이름이 뭐", "정체"]):
        return "저는 당신의 AI 비서 자비스입니다."

    return None  # 처리 못 함 → LLM 두뇌로 넘긴다


def _strip_keywords(text: str, keywords: list[str]) -> str:
    """문장에서 명령 키워드를 빼고 실제 검색어만 남긴다."""
    out = text
    for k in keywords:
        out = out.replace(k, " ")
    return " ".join(out.split()).strip()
