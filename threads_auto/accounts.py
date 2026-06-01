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
    """화면 표시용(토큰은 숨김)."""
    return [
        {"id": a["id"], "label": a.get("label", "계정"),
         "user_id": a.get("user_id", "")}
        for a in list_accounts()
    ]


def add_account(label: str, user_id: str, token: str) -> dict:
    items = list_accounts()
    acc = {
        "id": uuid.uuid4().hex[:8],
        "label": (label or "계정").strip(),
        "user_id": user_id.strip(),
        "access_token": token.strip(),
    }
    items.append(acc)
    _save_raw(items)
    return acc


def delete_account(acc_id: str) -> None:
    _save_raw([a for a in list_accounts() if a["id"] != acc_id])


def get_account(acc_id: str) -> dict | None:
    for a in list_accounts():
        if a["id"] == acc_id:
            return a
    return None
