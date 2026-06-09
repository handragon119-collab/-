"""특정 글을 '예약 시각'에 자동 발행하는 예약 큐.

저장 위치: data/scheduled.json (gitignore — 토큰은 없지만 개인 글이므로 로컬 보관)
각 항목: {id, text, run_at(epoch ms), account_ids, image_urls, video_url,
          topic, status(pending|done|failed|canceled), result, created}
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

PATH = Path("data/scheduled.json")


def _load() -> list[dict]:
    if PATH.exists():
        try:
            return json.loads(PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def _save(items: list[dict]) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def add(text: str, run_at_ms: int, account_ids: list[str] | None = None,
        image_urls: list[str] | None = None, video_url: str | None = None,
        topic: str | None = None) -> dict:
    items = _load()
    item = {
        "id": uuid.uuid4().hex[:8],
        "text": text,
        "run_at": int(run_at_ms),
        "account_ids": account_ids or [],
        "image_urls": image_urls or [],
        "video_url": video_url,
        "topic": topic,
        "status": "pending",
        "result": None,
        "created": int(time.time() * 1000),
    }
    items.append(item)
    _save(items)
    return item


def list_all() -> list[dict]:
    """예약 시각 순으로 정렬해 반환."""
    return sorted(_load(), key=lambda x: x.get("run_at", 0))


def delete(item_id: str) -> None:
    _save([i for i in _load() if i.get("id") != item_id])


def due(now_ms: int | None = None) -> list[dict]:
    """발행 시각이 된 pending 항목들."""
    now = now_ms or int(time.time() * 1000)
    return [i for i in _load()
            if i.get("status") == "pending" and i.get("run_at", 0) <= now]


def mark(item_id: str, status: str, result=None) -> None:
    items = _load()
    for i in items:
        if i.get("id") == item_id:
            i["status"] = status
            if result is not None:
                i["result"] = result
    _save(items)
