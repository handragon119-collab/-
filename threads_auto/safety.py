"""밴·노출제한 위험을 줄이기 위한 안전장치 모음.

- 일일 게시 한도 체크 (API rate limit 초과 방지)
- 최근 글과의 중복/유사도 검사 (스팸·중복 콘텐츠 탐지 회피)
- 게시 기록(posted_log.jsonl)을 기준으로 판단
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

LOG_PATH = Path("data/posted_log.jsonl")


def _read_log() -> list[dict]:
    """게시 기록을 읽어 리스트로 반환합니다. 없으면 빈 리스트."""
    if not LOG_PATH.exists():
        return []
    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def count_posts_last_24h(records: list[dict] | None = None) -> int:
    """최근 24시간 동안 게시한 글 수를 셉니다."""
    records = _read_log() if records is None else records
    cutoff = datetime.now() - timedelta(hours=24)
    count = 0
    for r in records:
        ts = r.get("time")
        if not ts:
            continue
        try:
            if datetime.fromisoformat(ts) >= cutoff:
                count += 1
        except ValueError:
            continue
    return count


def check_daily_limit(limit: int) -> tuple[bool, int]:
    """일일 한도 이내인지 확인합니다. (게시 가능 여부, 최근 24h 게시 수) 반환."""
    posted = count_posts_last_24h()
    return posted < limit, posted


def _similarity(a: str, b: str) -> float:
    """두 글의 유사도(0~1)를 반환합니다."""
    return SequenceMatcher(None, a, b).ratio()


def is_duplicate(text: str, threshold: float, lookback: int) -> tuple[bool, float]:
    """최근 글들과 비교해 중복(유사)인지 판단합니다. (중복 여부, 최대 유사도) 반환."""
    records = _read_log()
    recent = [r.get("text", "") for r in records[-lookback:] if r.get("text")]
    if not recent:
        return False, 0.0
    max_sim = max(_similarity(text, prev) for prev in recent)
    return max_sim >= threshold, max_sim
