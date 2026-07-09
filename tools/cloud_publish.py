"""클라우드(GitHub Actions)에서 예약 글을 발행하는 스크립트.

맥 없이도 24시간 돌아간다. 저장소 안의 prepared_posts.json(원고)과
assets/cardnews(카드 이미지)만으로 발행하며, 계정 토큰만 환경변수로 받는다.

- 발행 시각(run_at, KST)이 지난 글 중 아직 안 올린 것을 발행.
- 이미 올린 글은 cloud_state/posted.json 에 기록해 중복 방지.
- 너무 오래 지난 글(기본 3시간 초과)은 도배 방지를 위해 '건너뜀' 처리.

환경변수:
  THREADS_ACCOUNTS = {"pnent_official":"<토큰>","pm_ent2026":"<토큰>","moki_ent":"<토큰>", ...}
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from threads_auto.threads_client import ThreadsClient  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
PREPARED = ROOT / "prepared_posts.json"
STATE = ROOT / "cloud_state" / "posted.json"

GRACE_HOURS = 3     # 이보다 오래 지난 글은 발행하지 않고 건너뜀(도배 방지)
MAX_PER_RUN = 12    # 한 번 실행에 최대 발행 수(레이트리밋 안전장치)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Safari/605.1"}


def _host(data: bytes, ext: str = "png") -> str:
    errs = []
    try:
        r = requests.post("https://catbox.moe/user/api.php",
                          data={"reqtype": "fileupload"},
                          files={"fileToUpload": (f"f.{ext}", data)},
                          headers=_UA, timeout=90)
        r.raise_for_status()
        u = r.text.strip()
        if u.startswith("http"):
            return u
        errs.append(f"catbox:{u[:60]}")
    except Exception as e:  # noqa: BLE001
        errs.append(f"catbox:{e}")
    try:
        r = requests.post("https://0x0.st", files={"file": (f"f.{ext}", data)},
                          headers=_UA, timeout=90)
        r.raise_for_status()
        u = r.text.strip()
        if u.startswith("http"):
            return u
        errs.append(f"0x0:{u[:60]}")
    except Exception as e:  # noqa: BLE001
        errs.append(f"0x0:{e}")
    r = requests.post("https://tmpfiles.org/api/v1/upload",
                      files={"file": (f"f.{ext}", data)}, headers=_UA, timeout=90)
    r.raise_for_status()
    u = (r.json().get("data") or {}).get("url", "")
    if not u.startswith("http"):
        raise RuntimeError("이미지 호스팅 실패: " + " / ".join(errs))
    return u.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)


def _load_state() -> set:
    if STATE.exists():
        try:
            return set(json.loads(STATE.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            return set()
    return set()


def _save_state(posted: set) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(sorted(posted), ensure_ascii=False, indent=1),
                     encoding="utf-8")


def main() -> int:
    raw = os.environ.get("THREADS_ACCOUNTS", "").strip()
    if not raw:
        print("❌ THREADS_ACCOUNTS 환경변수가 없어요. GitHub Secrets에 등록하세요.")
        return 1
    try:
        tokens = json.loads(raw)
    except json.JSONDecodeError:
        print("❌ THREADS_ACCOUNTS 가 올바른 JSON이 아니에요.")
        return 1
    tokens = {k.lstrip("@").lower(): v for k, v in tokens.items()}

    entries = json.loads(PREPARED.read_text(encoding="utf-8"))
    posted = _load_state()
    now = dt.datetime.now(KST)
    grace = now - dt.timedelta(hours=GRACE_HOURS)

    def when(e):
        return dt.datetime.strptime(e["run_at"], "%Y-%m-%d %H:%M").replace(tzinfo=KST)

    due = []
    for e in entries:
        if e.get("id") in posted:
            continue
        try:
            t = when(e)
        except (ValueError, KeyError):
            continue
        if t <= now:
            due.append((t, e))
    due.sort(key=lambda x: x[0])

    published = skipped = failed = 0
    for t, e in due:
        eid = e["id"]
        if t < grace:                       # 너무 오래 지난 글 → 발행 없이 건너뜀
            posted.add(eid); skipped += 1
            continue
        if published >= MAX_PER_RUN:
            break
        uname = (e.get("username") or "").lstrip("@").lower()
        token = tokens.get(uname)
        if not token:
            print(f"  ⚠️ 토큰 없음(@{uname}) — 건너뜀 {eid}")
            posted.add(eid); skipped += 1
            continue
        try:
            urls = []
            for p in (e.get("image_files") or []):
                fp = ROOT / p
                if fp.exists():
                    urls.append(_host(fp.read_bytes(), fp.suffix.lstrip(".") or "png"))
            client = ThreadsClient("me", token)   # user_id는 토큰으로 자동 확인
            pid = client.post_media(e.get("text", ""), image_urls=urls)
            posted.add(eid); published += 1
            print(f"  ✅ 발행 @{uname} {eid} (이미지 {len(urls)}장) → {pid}")
            time.sleep(3)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  ❌ 실패 @{uname} {eid}: {str(exc)[:200]}")

    _save_state(posted)
    print(f"\n요약: 발행 {published} · 건너뜀(지난 글) {skipped} · 실패 {failed} "
          f"· 남은 대기 {sum(1 for e in entries if e.get('id') not in posted)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
