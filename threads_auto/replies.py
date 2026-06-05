"""내 게시글에 달린 댓글에 자동으로 답글을 답니다(계정별 말투).

안전 원칙:
- '내 글에 달린 댓글'에만 답글 (남의 글에 자동 댓글 X → 스팸/정지 위험)
- 이미 답글 단 댓글은 건너뛰기(중복 방지), 1회 실행 답글 수 상한
threads_manage_replies 권한이 있는 토큰이 필요합니다.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

HANDLED_PATH = Path("data/replied_ids.json")


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


def run_for_account(account: dict, reply_fn, max_replies: int = 20,
                    posts_limit: int = 10) -> list[dict]:
    """한 계정의 최근 글에 달린 새 댓글에 답글을 답니다.

    reply_fn(post_text, comment_text) -> 답글 텍스트
    """
    from threads_auto.threads_client import ThreadsClient

    client = ThreadsClient(account["user_id"], account["access_token"])
    my_username = account.get("username", "")
    handled = _load_handled()
    results: list[dict] = []
    done = 0

    posts = client.get_my_posts(posts_limit)
    for p in posts:
        if done >= max_replies:
            break
        try:
            replies = client.get_replies(p["id"])
        except Exception:  # noqa: BLE001 (개별 글 실패는 건너뜀)
            continue
        for r in replies:
            if done >= max_replies:
                break
            rid = r.get("id")
            if not rid or rid in handled:
                continue
            if my_username and r.get("username", "") == my_username:
                handled.add(rid)  # 내 답글은 건너뜀
                continue
            ctext = (r.get("text") or "").strip()
            if not ctext:
                handled.add(rid)
                continue
            try:
                reply_text = reply_fn(p.get("text", ""), ctext)
                client.post_reply(reply_text, rid)
                results.append({"ok": True, "to": r.get("username", ""),
                                "comment": ctext, "reply": reply_text})
                handled.add(rid)
                done += 1
                time.sleep(2)  # 봇 패턴 회피
            except Exception as exc:  # noqa: BLE001
                results.append({"ok": False, "error": str(exc)})

    _save_handled(handled)
    return results
