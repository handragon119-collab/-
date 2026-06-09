"""여러 Threads 계정을 관리합니다.

계정 정보(사용자 ID + 액세스 토큰)는 data/accounts.json에 저장합니다.
(이 파일은 비밀 토큰을 담으므로 .gitignore에 제외되어 커밋되지 않습니다.)

accounts.json이 없고 .env에 단일 계정 정보가 있으면, 그걸 '기본 계정'으로
자동 시드합니다(기존 사용자 호환).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import config

ACCOUNTS_PATH = Path("data/accounts.json")


def _load_raw() -> list[dict]:
    if ACCOUNTS_PATH.exists():
        try:
            return json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def _save_raw(items: list[dict]) -> None:
    ACCOUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACCOUNTS_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_accounts() -> list[dict]:
    """등록된 계정 목록. 없으면 .env의 단일 계정을 시드합니다."""
    items = _load_raw()
    if not items and config.THREADS_USER_ID and config.THREADS_ACCESS_TOKEN:
        items = [{
            "id": uuid.uuid4().hex[:8],
            "label": "기본 계정",
            "user_id": config.THREADS_USER_ID,
            "access_token": config.THREADS_ACCESS_TOKEN,
        }]
        _save_raw(items)
    return items


def public_list() -> list[dict]:
    """화면 표시용(토큰은 숨김, 프로필 정보 포함)."""
    from threads_auto.pipeline import persona_label

    active = get_active()
    active_id = active["id"] if active else None
    return [
        {"id": a["id"], "label": a.get("label", "계정"),
         "user_id": a.get("user_id", ""),
         "username": a.get("username", ""),
         "profile_pic": a.get("profile_pic", ""),
         "persona": a.get("persona", "general"),
         "persona_label": persona_label(a.get("persona", "general")),
         "auto_reply": bool(a.get("auto_reply", False)),
         "active": a["id"] == active_id}
        for a in list_accounts()
    ]


def get_active() -> dict | None:
    """현재 활성(연결된) 계정. 없으면 첫 계정."""
    items = list_accounts()
    for a in items:
        if a.get("active"):
            return a
    return items[0] if items else None


def set_active(acc_id: str) -> dict | None:
    """활성 계정을 변경합니다."""
    items = list_accounts()
    found = False
    for a in items:
        a["active"] = (a["id"] == acc_id)
        found = found or a["active"]
    if not found and items:
        items[0]["active"] = True
    _save_raw(items)
    return get_active()


def _fetch_profile(user_id: str, token: str) -> dict:
    """Threads에서 프로필(username, 사진)을 가져옵니다. 실패하면 빈 dict."""
    try:
        from threads_auto.threads_client import ThreadsClient

        p = ThreadsClient(user_id, token).get_profile()
        return {
            "username": p.get("username", ""),
            "profile_pic": p.get("threads_profile_picture_url", ""),
        }
    except Exception:  # noqa: BLE001
        return {}


def add_account(label: str, user_id: str, token: str, persona: str = "general") -> dict:
    items = list_accounts()
    prof = _fetch_profile(user_id.strip(), token.strip())
    acc = {
        "id": uuid.uuid4().hex[:8],
        "label": (label or prof.get("username") or "계정").strip(),
        "user_id": user_id.strip(),
        "access_token": token.strip(),
        "username": prof.get("username", ""),
        "profile_pic": prof.get("profile_pic", ""),
        "persona": persona or "general",
        "auto_reply": False,  # 댓글 자동 답글(실시간 추적) on/off
        "active": len(items) == 0,  # 첫 계정이면 활성
    }
    items.append(acc)
    _save_raw(items)
    return acc


def set_persona(acc_id: str, persona: str) -> None:
    """계정의 페르소나(말투)를 변경합니다."""
    items = list_accounts()
    for a in items:
        if a["id"] == acc_id:
            a["persona"] = persona or "general"
    _save_raw(items)


def set_auto_reply(acc_id: str, on: bool) -> None:
    """계정의 '댓글 자동 답글(실시간 추적)' on/off를 저장합니다."""
    items = list_accounts()
    for a in items:
        if a["id"] == acc_id:
            a["auto_reply"] = bool(on)
    _save_raw(items)


def auto_reply_on(acc_id: str) -> bool:
    """이 계정의 자동 답글이 켜져 있는지(최신 저장값 기준)."""
    for a in list_accounts():
        if a["id"] == acc_id:
            return bool(a.get("auto_reply", False))
    return False


def refresh_profiles() -> list[dict]:
    """모든 계정의 프로필(username, 사진)을 다시 가져와 저장합니다."""
    items = list_accounts()
    for a in items:
        prof = _fetch_profile(a.get("user_id", ""), a.get("access_token", ""))
        if prof.get("username"):
            a["username"] = prof["username"]
            a["profile_pic"] = prof.get("profile_pic", "")
            if a.get("label") in ("기본 계정", "계정", ""):
                a["label"] = prof["username"]
    _save_raw(items)
    return items


def delete_account(acc_id: str) -> None:
    _save_raw([a for a in list_accounts() if a["id"] != acc_id])


def get_account(acc_id: str) -> dict | None:
    for a in list_accounts():
        if a["id"] == acc_id:
            return a
    return None
