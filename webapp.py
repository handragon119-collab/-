"""스레드 자동 업로드 — 웹 UI.

터미널 대신 브라우저에서 버튼으로 조작합니다.

실행:
    python3 webapp.py
그다음 브라우저에서 http://127.0.0.1:5050 접속.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import config
import random

from threads_auto import safety
from threads_auto.content_generator import (
    ContentGenerator,
    load_categorized_topics,
)
from threads_auto.threads_client import ThreadsClient, ThreadsError
from threads_auto.image_generator import ImageError, create_image_url_auto
from threads_auto.pipeline import ThreadsPipeline


def _resolve_topic(topic: str | None, category: str | None) -> str | None:
    """topic이 있으면 그대로, 없으면 카테고리(또는 전체)에서 무작위로 고릅니다."""
    if topic:
        return topic
    cats = load_categorized_topics()
    if category and category in cats:
        pool = cats[category]
    else:
        pool = [t for items in cats.values() for t in items]
    return random.choice(pool) if pool else None

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _HAS_APS = True
except Exception:  # APScheduler 없으면 스케줄 기능만 비활성화
    _HAS_APS = False

app = Flask(__name__)

LOG_PATH = Path("data/posted_log.jsonl")
TOPICS_PATH = Path("topics.txt")
ENV_PATH = Path(".env")

# ── 백그라운드 스케줄러 (자동 게시) ──
_scheduler = None
if _HAS_APS:
    _scheduler = BackgroundScheduler(timezone=config.TIMEZONE)
    _scheduler.start()


def _update_env(key: str, value: str) -> None:
    """.env 파일에서 key=value 한 줄을 갱신(없으면 추가)합니다."""
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _scheduled_job() -> None:
    """스케줄러가 호출하는 자동 게시 작업."""
    from threads_auto.runner import run_once

    try:
        run_once()
    except Exception as exc:  # noqa: BLE001
        print(f"[스케줄 작업 오류] {exc}")


# ──────────────────────────── 페이지 ────────────────────────────


@app.get("/")
def index():
    return render_template("index.html")


# ──────────────────────────── API ────────────────────────────


@app.get("/api/status")
def api_status():
    """키 설정 여부, 오늘 게시 수, 스케줄 상태를 반환합니다."""
    posted = safety.count_posts_last_24h()
    job = _scheduler.get_job("auto_post") if _scheduler else None
    return jsonify(
        {
            "has_anthropic": bool(config.ANTHROPIC_API_KEY),
            "has_threads": bool(config.THREADS_USER_ID and config.THREADS_ACCESS_TOKEN),
            "has_image": config.has_image_support(),
            "model": config.CLAUDE_MODEL,
            "posted_24h": posted,
            "daily_limit": config.DAILY_POST_LIMIT,
            "schedule_supported": _HAS_APS,
            "schedule_running": bool(job),
            "schedule_cron": config.SCHEDULE_CRON,
            "schedule_next": str(job.next_run_time) if job else None,
            "timezone": config.TIMEZONE,
        }
    )


@app.get("/api/categories")
def api_categories():
    """주제 카테고리 목록을 반환합니다."""
    cats = load_categorized_topics()
    return jsonify({"ok": True, "categories": list(cats.keys())})


@app.post("/api/random_topic")
def api_random_topic():
    """선택한 카테고리에서 주제 하나를 무작위로 골라 반환합니다(글 생성 안 함)."""
    import random

    data = request.get_json(silent=True) or {}
    category = (data.get("category") or "").strip() or None
    cats = load_categorized_topics()
    if category and category in cats:
        pool = cats[category]
    else:
        pool = [t for items in cats.values() for t in items]
    if not pool:
        return jsonify({"ok": False, "error": "주제가 없습니다. 📋 주제 탭에서 추가하세요."}), 400
    return jsonify({"ok": True, "topic": random.choice(pool), "category": category})


@app.post("/api/generate")
def api_generate():
    """AI로 글을 생성합니다(게시 안 함). topic 또는 category로 주제 지정 가능."""
    try:
        config.require_anthropic()
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip() or None
    category = (data.get("category") or "").strip() or None
    advanced = bool(data.get("advanced", True))  # 기본: 고급 파이프라인
    topic = _resolve_topic(topic, category)

    try:
        if advanced and topic:
            pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)
            result = pipe.run(topic)
            return jsonify({
                "ok": True, "text": result["text"], "topic": topic,
                "length": len(result["text"]), "meta": result["meta"],
            })
        # 기본(빠른) 모드 또는 폴백
        gen = ContentGenerator(
            api_key=config.ANTHROPIC_API_KEY,
            model=config.CLAUDE_MODEL,
            persona=config.THREADS_PERSONA,
        )
        text = gen.generate(topic)
        return jsonify({"ok": True, "text": text, "topic": topic, "length": len(text)})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"글 생성 실패: {exc}"}), 500


@app.post("/api/auto")
def api_auto():
    """카테고리에서 주제 자동 선택 → 글 생성 → (가능하면) 사진까지 한 번에.

    반환: {text, topic, image_url(없으면 null), image_error(있으면 사유)}
    """
    try:
        config.require_anthropic()
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    data = request.get_json(silent=True) or {}
    category = (data.get("category") or "").strip() or None
    topic = (data.get("topic") or "").strip() or None
    want_image = bool(data.get("with_image", True))
    advanced = bool(data.get("advanced", True))
    topic = _resolve_topic(topic, category)

    pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)
    meta = None
    try:
        if advanced and topic:
            result = pipe.run(topic)
            text = result["text"]
            meta = result["meta"]
        else:
            gen = ContentGenerator(
                api_key=config.ANTHROPIC_API_KEY,
                model=config.CLAUDE_MODEL,
                persona=config.THREADS_PERSONA,
            )
            text = gen.generate(topic)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"글 생성 실패: {exc}"}), 500

    image_url = None
    image_error = None
    if want_image and config.has_image_support():
        try:
            # 프리미엄 디자인 감성의 이미지 프롬프트
            prompt = pipe.image_prompt(text)
            image_url = create_image_url_auto(
                config.OPENAI_API_KEY,
                config.IMGUR_CLIENT_ID,
                prompt,
                model=config.OPENAI_IMAGE_MODEL,
                size=config.OPENAI_IMAGE_SIZE,
            )
        except Exception as exc:  # noqa: BLE001  (사진 실패해도 글은 살림)
            image_error = str(exc)

    return jsonify(
        {
            "ok": True,
            "text": text,
            "topic": topic,
            "length": len(text),
            "image_url": image_url,
            "image_error": image_error,
            "meta": meta,
        }
    )


@app.post("/api/generate_image")
def api_generate_image():
    """글 내용에 어울리는 이미지를 AI로 생성해 미리보기용 URL을 반환합니다."""
    try:
        config.require_anthropic()
        config.require_image()
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "이미지를 만들 글이 비어 있습니다."}), 400

    try:
        pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)
        prompt = pipe.image_prompt(text)
        image_url = create_image_url_auto(
            config.OPENAI_API_KEY,
            config.IMGUR_CLIENT_ID,
            prompt,
            model=config.OPENAI_IMAGE_MODEL,
            size=config.OPENAI_IMAGE_SIZE,
        )
        return jsonify({"ok": True, "image_url": image_url})
    except ImageError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"이미지 생성 실패: {exc}"}), 500


@app.post("/api/post")
def api_post():
    """입력된 글을 스레드에 게시합니다. image_url이 있으면 이미지와 함께 게시합니다."""
    try:
        config.require_threads()
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    image_url = (data.get("image_url") or "").strip() or None
    if not text:
        return jsonify({"ok": False, "error": "게시할 글이 비어 있습니다."}), 400
    if len(text) > 500:
        return jsonify({"ok": False, "error": f"글이 너무 깁니다({len(text)}자). 500자 이내로 줄여주세요."}), 400

    ok, posted = safety.check_daily_limit(config.DAILY_POST_LIMIT)
    if not ok:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": f"최근 24시간 게시 수({posted})가 한도({config.DAILY_POST_LIMIT})에 도달했습니다.",
                }
            ),
            429,
        )

    try:
        client = ThreadsClient(config.THREADS_USER_ID, config.THREADS_ACCESS_TOKEN)
        if image_url:
            post_id = client.post_image(text, image_url)
        else:
            post_id = client.post_text(text)
    except ThreadsError as exc:
        return jsonify({"ok": False, "error": f"게시 실패: {exc}"}), 502

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "topic": data.get("topic"),
        "text": text,
        "post_id": post_id,
        "image_url": image_url,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return jsonify({"ok": True, "post_id": post_id})


@app.get("/api/topics")
def api_get_topics():
    content = TOPICS_PATH.read_text(encoding="utf-8") if TOPICS_PATH.exists() else ""
    return jsonify({"ok": True, "content": content})


@app.post("/api/topics")
def api_save_topics():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    TOPICS_PATH.write_text(content, encoding="utf-8")
    return jsonify({"ok": True})


@app.get("/api/history")
def api_history():
    items = []
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    items.reverse()  # 최신순
    return jsonify({"ok": True, "items": items[:100]})


@app.post("/api/schedule")
def api_schedule():
    """자동 스케줄을 켜거나 끕니다."""
    if not _HAS_APS:
        return jsonify({"ok": False, "error": "APScheduler가 설치되지 않았습니다."}), 400

    data = request.get_json(silent=True) or {}
    action = data.get("action")  # "start" | "stop"
    cron = (data.get("cron") or config.SCHEDULE_CRON).strip()

    if action == "stop":
        if _scheduler.get_job("auto_post"):
            _scheduler.remove_job("auto_post")
        return jsonify({"ok": True, "running": False})

    if action == "start":
        try:
            trigger = CronTrigger.from_crontab(cron, timezone=config.TIMEZONE)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"ok": False, "error": f"잘못된 스케줄 형식입니다: {exc}"}), 400
        _update_env("SCHEDULE_CRON", cron)
        config.SCHEDULE_CRON = cron
        _scheduler.add_job(_scheduled_job, trigger, id="auto_post", replace_existing=True)
        job = _scheduler.get_job("auto_post")
        return jsonify({"ok": True, "running": True, "next": str(job.next_run_time)})

    return jsonify({"ok": False, "error": "알 수 없는 동작입니다."}), 400


if __name__ == "__main__":
    import os

    # 포트는 환경변수 PORT로 바꿀 수 있음. 기본 5050
    # (5000은 macOS의 AirPlay 수신 기능과 충돌하므로 피함)
    port = int(os.getenv("PORT", "5050"))
    print("=" * 50)
    print("  스레드 자동 업로드 웹 UI")
    print("  브라우저에서 아래 주소를 여세요:")
    print(f"  👉 http://127.0.0.1:{port}")
    print("  (종료하려면 이 창에서 Ctrl+C)")
    print("=" * 50)
    app.run(host="127.0.0.1", port=port, debug=False)
