"""조회수(도달) 극대화 전략 — 글 생성 시 최우선 지침으로 주입한다.

두 부분으로 구성:
1) REACH_STRATEGY: 플랫폼(스레드) 도달을 끌어올리는 '항상 적용' 전략(에버그린).
2) 계정별 데이터 노트: 실제 인사이트(📊분석)에서 학습된 '이 계정에서 통한 것'
   (잘 나온 시간대 / 잘 먹힌 글의 공통점). data/reach_strategy.json 에 저장.

분석을 돌릴 때마다(analytics.learn_from_results) 2)가 갱신되고,
다음 글 생성부터 1)+2)가 함께 반영된다.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

STRATEGY_PATH = Path("data/reach_strategy.json")

# ── 항상 적용되는 도달 극대화 전략 ──────────────────────────────
REACH_STRATEGY = """[‼️ 최우선 목표: 조회수(도달)를 최대로 끌어올린다]
이 글의 1차 목표는 '많은 사람이 보고 멈추고 반응하는 것'이다. 아래를 반드시 지켜라.

1) 첫 줄이 전부다(후킹).
   - 첫 줄에서 스크롤을 멈추게 만들어라. 밋밋한 인사/상황설명으로 시작 금지.
   - 다음 중 하나로 시작: 의외의 한마디 · 공감 후킹("나만 이래?") · 작은 반전 ·
     구체적 장면 · 솔직한 고백 · 궁금하게 만드는 미끼. 결론/핵심을 앞에 던져라.
2) 짧고 빠르게. 3~6줄, 한 줄은 짧게. 길고 늘어지면 끝까지 안 읽고 이탈한다.
3) 한 글 = 한 메시지. 여러 얘기 섞지 말고 하나만 또렷하게.
4) 공감·저장·공유가 되게. "맞아 나도" 또는 "이거 누구 보여주고 싶다" 소리가
   나오게 써라. 보편적 감정/경험을 구체적 디테일로 건드려라.
5) 자연스러운 반응 유발. 끝을 여운이나 가벼운 한마디로 닫아 댓글이 달리게 하되,
   '댓글 구걸'은 금지(가끔만 진짜 궁금한 질문 하나).
6) 매번 다른 후킹. 이전 글과 같은 첫 줄·같은 패턴 반복하면 도달이 죽는다.
7) 링크·해시태그 도배 금지(도달 떨어진다). 외부 링크 유도하지 마라.
8) 사람 냄새 나게. 광고처럼 들리면 사람들이 스킵한다. 진짜 사람이 쓴 것처럼."""


def _load() -> dict:
    if STRATEGY_PATH.exists():
        try:
            return json.loads(STRATEGY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save(d: dict) -> None:
    STRATEGY_PATH.parent.mkdir(parents=True, exist_ok=True)
    STRATEGY_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def get_note(account_id: str | None) -> dict:
    """계정의 데이터 학습 노트 {note, best_hours, updated} (없으면 빈 값)."""
    return _load().get(account_id or "", {})


def set_note(account_id: str | None, note: str = "",
             best_hours: list[int] | None = None) -> None:
    """📊분석에서 도출한 '이 계정에서 통한 것'을 저장."""
    if not account_id:
        return
    d = _load()
    d[account_id] = {
        "note": (note or "").strip(),
        "best_hours": best_hours or [],
        "updated": int(time.time() * 1000),
    }
    _save(d)


def get_block(account_id: str | None) -> str:
    """프롬프트에 넣을 전략 블록(에버그린 + 계정 학습 노트)."""
    block = REACH_STRATEGY
    n = get_note(account_id)
    extra = (n.get("note") or "").strip()
    hours = n.get("best_hours") or []
    if extra or hours:
        block += "\n\n[이 계정 실제 데이터에서 학습된 것 — 특히 반영하라]"
        if extra:
            block += "\n" + extra
        if hours:
            block += "\n· 조회 잘 나오는 시간대: " + ", ".join(f"{h}시" for h in hours)
    return block
