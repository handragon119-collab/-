"""내 게시글에 달린 댓글에 자동으로 답글을 답니다(계정별 말투).

안전 원칙:
- '내 글에 달린 댓글'에만 답글 (남의 글에 자동 댓글 X → 스팸/정지 위험)
- 이미 답글 단 댓글은 건너뛰기(중복 방지), 1회 실행 답글 수 상한
threads_manage_replies 권한이 있는 토큰이 필요합니다.
"""

from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path

HANDLED_PATH = Path("data/replied_ids.json")


def _to_epoch_ms(ts: str | None) -> int | None:
    """Threads 타임스탬프(ISO) → epoch ms."""
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return int(datetime.strptime(ts, fmt).timestamp() * 1000)
        except ValueError:
            continue
    return None


def _load_handled() -> set:
    if HANDLED_PATH.exists():
        try:
            return set(json.loads(HANDLED_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            return set()
    return set()


def _save_handled(s: set) -> None:
    HANDLED_PATH.parent.mkdir(parents=True, exist_ok=True)
    HANDLED_PATH.write_text(json.dumps(sorted(s), ensure_ascii=False), encoding="utf-8")


def _human_typing_delay(text: str) -> float:
    """사람이 댓글을 읽고 → 생각하고 → 타이핑하는 데 걸릴 법한 시간(초)."""
    read = random.uniform(2.0, 5.0)                 # 댓글 읽고 잠깐 생각
    typing = len(text) * random.uniform(0.12, 0.28)  # 글자당 타이핑 속도
    pauses = random.uniform(0.0, 4.0)               # 중간에 멈칫
    # 가끔(20%) 다른 일 하다 오는 것처럼 더 길게
    if random.random() < 0.2:
        pauses += random.uniform(8.0, 25.0)
    return read + typing + pauses


def run_for_account(account: dict, reply_fn, max_replies: int = 0,
                    posts_limit: int = 25, like_comments: bool = False,
                    human_typing: bool = True, on_result=None,
                    should_stop=None) -> list[dict]:
    """한 계정의 최근 글에 달린 새 댓글에 답글을 답니다.

    reply_fn(post_text, comment_text) -> 답글 텍스트
    max_replies: 0이면 '수량 제한 없이' 새 댓글 전부 (천천히, 사람처럼).
    on_result(result): 답글 하나 끝날 때마다 호출(실시간 보고서용).
    should_stop(): True 반환 시 중간에 멈춤.
    """
    from threads_auto.threads_client import ThreadsClient

    client = ThreadsClient(account["user_id"], account["access_token"])
    my_username = account.get("username", "")
    handled = _load_handled()
    results: list[dict] = []
    done = 0
    unlimited = not max_replies or max_replies <= 0

    posts = client.get_my_posts(posts_limit)
    for p in posts:
        if not unlimited and done >= max_replies:
            break
        if should_stop and should_stop():
            break
        try:
            replies = client.get_replies(p["id"])
        except Exception:  # noqa: BLE001
            continue
        for r in replies:
            if not unlimited and done >= max_replies:
                break
            if should_stop and should_stop():
                break
            rid = r.get("id")
            if not rid or rid in handled:
                continue
            if my_username and r.get("username", "") == my_username:
                handled.add(rid)
                continue
            ctext = (r.get("text") or "").strip()
            if not ctext:
                handled.add(rid)
                continue
            try:
                if like_comments:
                    try:
                        client.like(rid)
                    except Exception:  # noqa: BLE001
                        pass

                reply_text = reply_fn(p.get("text", ""), ctext)

                if human_typing:
                    time.sleep(_human_typing_delay(reply_text))
                else:
                    time.sleep(2)

                client.post_reply(reply_text, rid)
                item = {"ok": True, "to": r.get("username", ""),
                        "comment": ctext, "reply": reply_text,
                        "comment_epoch": _to_epoch_ms(r.get("timestamp")),
                        "reply_epoch": int(time.time() * 1000)}
                results.append(item)
                handled.add(rid)
                done += 1
                _save_handled(handled)  # 중간에 멈춰도 진행분 저장
                if on_result:
                    on_result(item)
            except Exception as exc:  # noqa: BLE001
                item = {"ok": False, "error": str(exc)}
                results.append(item)
                if on_result:
                    on_result(item)

    _save_handled(handled)
    return results
