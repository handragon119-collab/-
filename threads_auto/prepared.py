"""미리 준비된 글(prepared_posts.json)을 계정에 맞춰 자동 예약합니다.

원격(클라우드) 세션에서 글을 만들어 저장소에 커밋해 두면, 로컬 앱이
시작될 때(또는 예약 목록을 열 때) 이 파일을 읽어 @아이디가 일치하는
계정으로 자동 예약을 겁니다.

- 항목 형식: {id, username, text, run_at("YYYY-MM-DD HH:MM"), topic}
- 한 번 예약된 항목은 data/prepared_imported.json에 id가 기록되어
  중복 예약되지 않습니다. (파일을 다시 받아도 두 번 안 걸림)
- run_at이 이미 지난 시각이면 다음 날 같은 시각으로 미룹니다.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

PREPARED_PATH = Path("prepared_posts.json")
IMPORTED_PATH = Path("data/prepared_imported.json")


def _imported() -> set:
    if IMPORTED_PATH.exists():
        try:
            return set(json.loads(IMPORTED_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            return set()
    return set()


def _save_imported(s: set) -> None:
    IMPORTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    IMPORTED_PATH.write_text(
        json.dumps(sorted(s), ensure_ascii=False, indent=2), encoding="utf-8")


def import_pending() -> list[dict]:
    """미예약 항목을 계정에 매칭해 예약. 처리 결과 리스트 반환."""
    if not PREPARED_PATH.exists():
        return []
    try:
        entries = json.loads(PREPARED_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    from threads_auto import accounts, scheduled_posts

    accs = accounts.list_accounts()
    done = _imported()
    results: list[dict] = []
    changed = False
    refreshed = False  # 프로필 새로고침은 한 번만

    def _match(uname: str):
        return next((a for a in accs
                     if (a.get("username") or "").lower() == uname
                     or (uname and uname in (a.get("label") or "").lower())), None)

    for e in entries:
        eid = e.get("id")
        if not eid or eid in done:
            continue
        uname = (e.get("username") or "").lstrip("@").strip().lower()
        text = (e.get("text") or "").strip()
        if not uname or not text:
            continue
        # @아이디 우선, 없으면 계정 이름(label)에 포함돼도 인정
        acc = _match(uname)
        if not acc and not refreshed:
            # 등록 직후라 @아이디가 아직 비어있을 수 있음 → 한 번 새로고침 후 재시도
            refreshed = True
            try:
                accs = accounts.refresh_profiles()
                acc = _match(uname)
            except Exception:  # noqa: BLE001
                pass
        if not acc:
            results.append({"id": eid, "ok": False,
                            "error": f"@{uname} 계정을 못 찾았어요. 계정 탭에서 "
                                     "'계정 정보 새로고침' 후 자동 탭을 다시 여세요."})
            continue
        try:
            dt = datetime.strptime(e.get("run_at", ""), "%Y-%m-%d %H:%M")
        except ValueError:
            results.append({"id": eid, "ok": False, "error": "run_at 형식 오류"})
            continue
        now = datetime.now()
        while dt <= now + timedelta(minutes=2):  # 지난 시각이면 다음 날로
            dt += timedelta(days=1)
        item = scheduled_posts.add(
            text, int(dt.timestamp() * 1000), [acc["id"]], topic=e.get("topic"),
            image_files=e.get("image_files") or [],
            preview_urls=e.get("preview_urls") or [])
        done.add(eid)
        changed = True
        results.append({"id": eid, "ok": True, "account": acc.get("label"),
                        "username": acc.get("username", ""),
                        "run_at": dt.strftime("%m/%d %H:%M"),
                        "item_id": item["id"]})

    if changed:
        _save_imported(done)
    return results
