"""스레드 자동 업로드 — 웹 UI.

터미널 대신 브라우저에서 버튼으로 조작합니다.

실행:
    python3 webapp.py
그다음 브라우저에서 http://127.0.0.1:5050 접속.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

import config
import random

from threads_auto import safety
from threads_auto import accounts
from threads_auto import samples
from threads_auto import scheduled_posts
from threads_auto.content_generator import (
    ContentGenerator,
    load_categorized_topics,
)
from threads_auto.threads_client import ThreadsClient, ThreadsError
from threads_auto.image_generator import ImageError, generate_image
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


def _active_persona():
    """현재 활성 계정의 (페르소나, 학습예시, 계정ID)를 반환."""
    from threads_auto import samples
    acc = accounts.get_active()
    if not acc:
        return "general", [], None
    persona = acc.get("persona", "general")
    examples = samples.get_samples(acc["id"], persona, limit=10)
    return persona, examples, acc["id"]

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
    active = accounts.get_active()
    return jsonify(
        {
            "active_account": (("@" + active["username"]) if active and active.get("username") else (active.get("label") if active else None)),
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

    persona, examples, acc_id = _active_persona()
    lessons = samples.get_edit_lessons(acc_id)
    try:
        if advanced and topic:
            pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)
            result = pipe.run(topic, persona=persona, examples=examples,
                              category=category, edit_lessons=lessons)
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

    persona, examples, acc_id = _active_persona()
    lessons = samples.get_edit_lessons(acc_id)
    pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)
    meta = None
    try:
        if advanced and topic:
            result = pipe.run(topic, persona=persona, examples=examples,
                              category=category, edit_lessons=lessons)
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
    preview_url = None
    image_error = None
    if want_image and config.has_image_support():
        try:
            # 프리미엄 디자인 감성의 이미지 프롬프트
            prompt = pipe.image_prompt(text)
            made = _make_ai_image(prompt)
            preview_url = made["preview_url"]
            image_url = made["image_url"]
            image_error = made["image_error"]
        except Exception as exc:  # noqa: BLE001  (사진 실패해도 글은 살림)
            image_error = str(exc)

    return jsonify(
        {
            "ok": True,
            "text": text,
            "topic": topic,
            "length": len(text),
            "image_url": image_url,
            "preview_url": preview_url,
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
        made = _make_ai_image(prompt)
        return jsonify({"ok": True, "image_url": made["image_url"],
                        "preview_url": made["preview_url"],
                        "image_error": made["image_error"]})
    except ImageError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"이미지 생성 실패: {exc}"}), 500


_MEDIA_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "webp": "image/webp", "gif": "image/gif",
}
_VIDEO_EXTS = {"mp4", "mov", "m4v", "webm", "avi"}


def _host_bytes(data: bytes, ext: str) -> str:
    """이미지/영상 바이트를 공개 URL로 호스팅. 영상은 항상 터널 사용."""
    is_video = ext in _VIDEO_EXTS
    if config.IMGUR_CLIENT_ID and not is_video:
        from threads_auto.image_generator import upload_to_imgur
        return upload_to_imgur(config.IMGUR_CLIENT_ID, data)
    from threads_auto import tunnel_host
    return tunnel_host.host_image(data, ext=ext)


# 미리보기용: 생성/업로드한 미디어를 이 앱(Flask)에서 직접 제공합니다.
# (공개 호스팅 URL은 Threads '게시'에만 필요하고, 브라우저 미리보기에는
#  로컬 주소가 더 빠르고 확실합니다. 터널/Imgur가 안 떠도 미리보기는 보입니다.)
IMAGES_DIR = Path("data/images")


def _save_preview(data: bytes, ext: str) -> str:
    """미디어 바이트를 data/images에 저장하고 로컬 미리보기 URL(/media/...)을 반환."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ext = (ext or "png").lstrip(".").lower()
    if ext not in _MEDIA_TYPES and ext not in _VIDEO_EXTS:
        ext = "png"
    name = f"{uuid.uuid4().hex}.{ext}"
    (IMAGES_DIR / name).write_bytes(data)
    return f"/media/{name}"


@app.get("/media/<path:name>")
def media_file(name: str):
    """미리보기용 로컬 미디어 제공."""
    return send_from_directory(IMAGES_DIR.resolve(), name)


def _make_ai_image(prompt: str) -> dict:
    """AI 이미지를 1번 생성해서 {preview_url, image_url, image_error}를 반환.

    - preview_url: 브라우저 미리보기용(로컬 Flask). 항상 채워짐.
    - image_url: 게시용 공개 URL. 호스팅(Imgur/터널) 실패 시 None + image_error.
    """
    img_bytes = generate_image(
        config.OPENAI_API_KEY, prompt,
        model=config.OPENAI_IMAGE_MODEL, size=config.OPENAI_IMAGE_SIZE,
    )
    preview_url = _save_preview(img_bytes, "png")
    image_url, image_error = None, None
    try:
        image_url = _host_bytes(img_bytes, "png")
    except Exception as exc:  # noqa: BLE001 (미리보기는 살리고, 게시용만 실패 처리)
        image_error = (
            "사진 미리보기는 됐지만, 게시용 공개주소 만들기에 실패했어요: "
            + str(exc)
        )
    return {"preview_url": preview_url, "image_url": image_url,
            "image_error": image_error}


@app.post("/api/upload_media")
def api_upload_media():
    """사진 여러 장 또는 동영상 1개를 업로드합니다.

    form: files[] (여러 개), write=="1"이면 AI가 보고 글까지 작성.
    반환: {image_urls:[...], video_url, text}
    """
    files = request.files.getlist("files") or ([request.files["file"]] if "file" in request.files else [])
    files = [f for f in files if f and f.filename]
    if not files:
        return jsonify({"ok": False, "error": "파일이 없습니다."}), 400

    want_write = request.form.get("write") == "1"
    first_ext = files[0].filename.rsplit(".", 1)[-1].lower() if "." in files[0].filename else ""
    is_video = first_ext in _VIDEO_EXTS

    video_preview = None
    preview_urls: list[str] = []
    try:
        if is_video:
            f = files[0]
            data = f.read()
            if len(data) > 100 * 1024 * 1024:
                return jsonify({"ok": False, "error": "영상이 너무 큽니다(100MB 이하)."}), 400
            video_preview = _save_preview(data, first_ext)  # 미리보기(로컬)
            video_url = _host_bytes(data, first_ext)        # 게시용(공개)
            image_urls = []
            # 영상 분석용 프레임 추출 → 보관(글쓰기용)
            frames = []
            if want_write:
                import tempfile, os
                from threads_auto import video_frames
                with tempfile.NamedTemporaryFile(suffix="." + first_ext, delete=False) as tmp:
                    tmp.write(data); tmp_path = tmp.name
                try:
                    frames = video_frames.extract_frames(tmp_path, max_frames=5)
                finally:
                    os.unlink(tmp_path)
        else:
            video_url = None
            image_urls = []
            frames = []
            for f in files[:10]:
                data = f.read()
                if len(data) > 8 * 1024 * 1024:
                    return jsonify({"ok": False, "error": f"{f.filename}: 8MB 이하만 가능."}), 400
                ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "png"
                preview_urls.append(_save_preview(data, ext))  # 미리보기(로컬)
                image_urls.append(_host_bytes(data, ext))       # 게시용(공개)
                frames.append((data, _MEDIA_TYPES.get(ext, "image/png")))
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"업로드 실패: {exc}"}), 500

    # AI 글 작성
    text = None
    text_error = None
    if want_write:
        try:
            config.require_anthropic()
            pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)
            from threads_auto.pipeline import persona_style, persona_vision_mode, persona_facts
            persona, examples, _ = _active_persona()
            style_extra = persona_style(persona)
            vmode = persona_vision_mode(persona)
            facts = persona_facts(persona)
            if is_video:
                imgs = [(fr, "image/jpeg") for fr in frames]
                text = pipe.write_from_images(imgs, is_video=True, style_extra=style_extra, examples=examples, vision_mode=vmode, facts=facts)
            else:
                text = pipe.write_from_images(frames, is_video=False, style_extra=style_extra, examples=examples, vision_mode=vmode, facts=facts)
        except Exception as exc:  # noqa: BLE001
            text_error = str(exc)

    return jsonify({
        "ok": True, "image_urls": image_urls, "video_url": video_url,
        "preview_urls": preview_urls, "video_preview": video_preview,
        "text": text, "text_error": text_error,
    })


@app.get("/api/accounts")
def api_accounts():
    """등록된 계정 목록(토큰 숨김)을 반환합니다."""
    return jsonify({"ok": True, "accounts": accounts.public_list()})


@app.get("/api/personas")
def api_personas():
    """선택 가능한 페르소나(말투) 목록."""
    from threads_auto.pipeline import PERSONAS
    return jsonify({"ok": True, "personas": [{"id": k, "label": v[0]} for k, v in PERSONAS.items()]})


@app.post("/api/accounts")
def api_add_account():
    """계정을 추가합니다. (label, user_id, access_token, persona)"""
    data = request.get_json(silent=True) or {}
    label = (data.get("label") or "").strip()
    user_id = (data.get("user_id") or "").strip()
    token = (data.get("access_token") or "").strip()
    persona = (data.get("persona") or "general").strip()
    if not user_id or not token:
        return jsonify({"ok": False, "error": "사용자 ID와 토큰을 모두 입력하세요."}), 400
    if not token.isascii():
        return jsonify({"ok": False, "error": "토큰에 한글·공백이 섞였습니다. 다시 확인하세요."}), 400
    acc = accounts.add_account(label, user_id, token, persona=persona)
    return jsonify({"ok": True, "id": acc["id"]})


@app.post("/api/accounts/persona")
def api_set_persona():
    """계정의 페르소나(말투)를 변경합니다."""
    data = request.get_json(silent=True) or {}
    accounts.set_persona((data.get("id") or "").strip(), (data.get("persona") or "general").strip())
    return jsonify({"ok": True, "accounts": accounts.public_list()})


@app.post("/api/accounts/delete")
def api_delete_account():
    data = request.get_json(silent=True) or {}
    accounts.delete_account((data.get("id") or "").strip())
    return jsonify({"ok": True})


@app.post("/api/accounts/refresh")
def api_refresh_accounts():
    """각 계정의 스레드 프로필(아이디·사진)을 다시 가져옵니다."""
    accounts.refresh_profiles()
    return jsonify({"ok": True, "accounts": accounts.public_list()})


@app.post("/api/accounts/active")
def api_set_active():
    """현재 연결(활성) 계정을 변경합니다."""
    data = request.get_json(silent=True) or {}
    acc = accounts.set_active((data.get("id") or "").strip())
    return jsonify({"ok": True, "active": acc["username"] if acc else None,
                    "accounts": accounts.public_list()})


def _publish(text: str, image_urls: list, video_url, targets: list,
             topic=None) -> list:
    """대상 계정들에 실제 게시 + 기록 + 계정별 학습. results 리스트 반환.

    (즉시 게시 /api/post 와 예약 발행 워처가 공유하는 핵심 로직)
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for a in targets:
        try:
            client = ThreadsClient(a["user_id"], a["access_token"])
            post_id = client.post_media(text, image_urls=image_urls, video_url=video_url)
            results.append({"label": a["label"], "ok": True, "post_id": post_id})
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "account": a["label"],
                    "topic": topic,
                    "text": text,
                    "post_id": post_id,
                    "image_urls": image_urls,
                    "video_url": video_url,
                }, ensure_ascii=False) + "\n")
        except Exception as exc:  # noqa: BLE001
            results.append({"label": a["label"], "ok": False, "error": str(exc)})

    success = sum(1 for r in results if r["ok"])
    # 학습: 게시 성공한 '계정별'로 그 글을 학습 예시에 저장 (계정마다 톤 따로 쌓임)
    if success > 0:
        try:
            from threads_auto import samples
            for a, r in zip(targets, results):
                if r.get("ok"):
                    samples.add_sample(a["id"], text)
        except Exception:  # noqa: BLE001
            pass
    return results


@app.post("/api/post")
def api_post():
    """선택한 계정(들)에 글을 게시합니다. image_url이 있으면 이미지와 함께 게시."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    # 미디어: 단일 image_url(구버전) 또는 image_urls(여러 장), video_url
    image_urls = data.get("image_urls") or ([data["image_url"]] if data.get("image_url") else [])
    image_urls = [u for u in image_urls if u]
    video_url = (data.get("video_url") or "").strip() or None
    if not text:
        return jsonify({"ok": False, "error": "게시할 글이 비어 있습니다."}), 400
    if len(text) > 500:
        return jsonify({"ok": False, "error": f"글이 너무 깁니다({len(text)}자). 500자 이내로 줄여주세요."}), 400

    # 게시 대상 계정 선택 (account_ids 없으면 전체)
    all_accs = accounts.list_accounts()
    if not all_accs:
        return jsonify({"ok": False, "error": "등록된 계정이 없습니다. '계정' 탭에서 추가하세요."}), 400
    acc_ids = data.get("account_ids") or []
    targets = [a for a in all_accs if a["id"] in acc_ids] if acc_ids else all_accs
    if not targets:
        return jsonify({"ok": False, "error": "게시할 계정을 선택하세요."}), 400

    ok, posted = safety.check_daily_limit(config.DAILY_POST_LIMIT)
    if not ok:
        return jsonify({
            "ok": False,
            "error": f"최근 24시간 게시 수({posted})가 한도({config.DAILY_POST_LIMIT})에 도달했습니다.",
        }), 429

    results = _publish(text, image_urls, video_url, targets, data.get("topic"))
    success = sum(1 for r in results if r["ok"])
    return jsonify({"ok": success > 0, "results": results,
                    "summary": f"{success}/{len(results)} 계정 게시 성공"})


# 답글 작업 상태(백그라운드 실행 + 실시간 보고서)
_reply_job = {"running": False, "results": [], "summary": "", "stop": False}


@app.post("/api/reply_run")
def api_reply_run():
    """현재 계정의 새 댓글에 자동 답글을 백그라운드로 답니다(수량 제한 없음, 사람처럼)."""
    if _reply_job["running"]:
        return jsonify({"ok": True, "running": True, "already": True})
    try:
        config.require_anthropic()
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    acc = accounts.get_active()
    if not acc:
        return jsonify({"ok": False, "error": "연결된 계정이 없어요."}), 400

    data = request.get_json(silent=True) or {}
    max_replies = int(data.get("max", 0))  # 0 = 수량 제한 없음

    from threads_auto.pipeline import persona_style, persona_facts
    from threads_auto import samples, replies as replies_mod
    persona = acc.get("persona", "general")
    style_extra = persona_style(persona)
    facts = persona_facts(persona)
    examples = samples.get_samples(acc["id"], persona, limit=8)
    pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)

    def reply_fn(post_text, comment_text):
        return pipe.write_reply(style_extra, examples, post_text, comment_text, facts=facts)

    _reply_job.update(running=True, results=[], summary="진행 중…", stop=False)

    def work():
        try:
            replies_mod.run_for_account(
                acc, reply_fn, max_replies=max_replies,
                like_comments=bool(data.get("like", False)), human_typing=True,
                on_result=lambda it: _reply_job["results"].append(it),
                should_stop=lambda: _reply_job["stop"],
            )
            s = sum(1 for r in _reply_job["results"] if r.get("ok"))
            _reply_job["summary"] = (f"{s}개 댓글에 답글을 달았어요." if s else "새로 답글 달 댓글이 없어요.")
        except ThreadsError as exc:
            msg = str(exc)
            if "permission" in msg.lower() or "scope" in msg.lower() or "OAuth" in msg:
                msg = ("답글 권한이 없어요. 토큰에 'threads_manage_replies' 권한을 추가하고 "
                       "토큰을 다시 발급받아 계정을 등록하세요.")
            _reply_job["summary"] = "오류: " + msg
        except Exception as exc:  # noqa: BLE001
            _reply_job["summary"] = "오류: " + str(exc)
        finally:
            _reply_job["running"] = False

    threading.Thread(target=work, daemon=True).start()
    return jsonify({"ok": True, "running": True})


@app.get("/api/reply_status")
def api_reply_status():
    return jsonify({"ok": True, "running": _reply_job["running"],
                    "results": _reply_job["results"], "summary": _reply_job["summary"]})


@app.post("/api/reply_stop")
def api_reply_stop():
    _reply_job["stop"] = True
    return jsonify({"ok": True})


# ──────────────────────────────────────────────────────────────────────
# 댓글 자동 답글 '실시간 추적' — 계정마다 on/off (백그라운드 워처)
#
# 앱이 켜져 있는 동안, auto_reply가 켜진 계정들의 새 댓글을 주기적으로
# 점검해 그 계정 말투로 바로바로 답글을 답니다. 이미 답한 댓글은 건너뜁니다.
# ──────────────────────────────────────────────────────────────────────
WATCH_INTERVAL = 60          # 점검 주기(초)
_reply_lock = threading.Lock()  # 수동 답글 작업과 겹치지 않도록
_auto_reply = {
    "started": False,
    "activity": [],          # 최근 답글 내역(여러 계정 합쳐서, 최신이 뒤)
    "last_cycle": None,      # 마지막 점검 시각(epoch ms)
    "active": [],            # 지금 켜진 계정 username/label 목록
}


def _auto_reply_for(acc: dict) -> None:
    """한 계정의 새 댓글을 점검해 자동 답글을 답니다(워처 1회분)."""
    from threads_auto.pipeline import persona_style, persona_facts
    from threads_auto import samples, replies as replies_mod

    persona = acc.get("persona", "general")
    style_extra = persona_style(persona)
    facts = persona_facts(persona)
    examples = samples.get_samples(acc["id"], persona, limit=8)
    pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)
    who = acc.get("username") or acc.get("label") or "계정"

    def reply_fn(post_text, comment_text):
        return pipe.write_reply(style_extra, examples, post_text, comment_text, facts=facts)

    def on_result(it):
        item = {**it, "account": who, "ts": int(time.time() * 1000)}
        _auto_reply["activity"].append(item)
        _auto_reply["activity"] = _auto_reply["activity"][-100:]

    with _reply_lock:
        replies_mod.run_for_account(
            acc, reply_fn, max_replies=0, posts_limit=80,
            human_typing=True, on_result=on_result,
            # 도중에 사용자가 이 계정의 자동 답글을 끄면 멈춤
            should_stop=lambda: not accounts.auto_reply_on(acc["id"]),
        )


def _auto_reply_loop():
    """켜진 계정들을 주기적으로 순회하며 새 댓글에 자동 답글."""
    while True:
        try:
            if config.ANTHROPIC_API_KEY:
                on_accs = [a for a in accounts.list_accounts() if a.get("auto_reply")]
                _auto_reply["active"] = [
                    (a.get("username") or a.get("label") or "계정") for a in on_accs
                ]
                for acc in on_accs:
                    if not accounts.auto_reply_on(acc["id"]):
                        continue
                    try:
                        _auto_reply_for(acc)
                    except Exception:  # noqa: BLE001 (한 계정 실패가 전체를 멈추지 않게)
                        pass
            _auto_reply["last_cycle"] = int(time.time() * 1000)
        except Exception:  # noqa: BLE001
            pass
        # 다음 점검까지 대기(1초씩 쪼개 종료 신호에 빠르게 반응)
        for _ in range(WATCH_INTERVAL):
            time.sleep(1)


def _ensure_auto_reply_watcher():
    if _auto_reply["started"]:
        return
    _auto_reply["started"] = True
    threading.Thread(target=_auto_reply_loop, daemon=True).start()


@app.post("/api/accounts/auto_reply")
def api_account_auto_reply():
    """계정별 댓글 자동 답글 on/off 토글."""
    data = request.get_json(silent=True) or {}
    acc_id = data.get("id")
    on = bool(data.get("on"))
    if not acc_id:
        return jsonify({"ok": False, "error": "계정 ID가 없어요."}), 400
    if on:
        try:
            config.require_anthropic()
        except RuntimeError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
    accounts.set_auto_reply(acc_id, on)
    _ensure_auto_reply_watcher()
    return jsonify({"ok": True, "on": on})


@app.get("/api/auto_reply_status")
def api_auto_reply_status():
    """자동 답글 워처 상태 + 최근 답글 내역."""
    return jsonify({
        "ok": True,
        "active": _auto_reply["active"],
        "last_cycle": _auto_reply["last_cycle"],
        "interval": WATCH_INTERVAL,
        "activity": _auto_reply["activity"][-40:],
    })


# ── 성과 분석(인사이트) ──
_insights_job = {"running": False, "done": 0, "total": 0, "result": None, "error": ""}


@app.post("/api/insights_run")
def api_insights_run():
    """현재(또는 지정) 계정의 최근 글 성과를 백그라운드로 분석합니다."""
    if _insights_job["running"]:
        return jsonify({"ok": True, "running": True, "already": True})
    data = request.get_json(silent=True) or {}
    acc_id = data.get("id")
    acc = accounts.get_account(acc_id) if acc_id else accounts.get_active()
    if not acc:
        return jsonify({"ok": False, "error": "연결된 계정이 없어요."}), 400
    limit = int(data.get("limit", 25))

    from threads_auto import analytics
    akey = config.ANTHROPIC_API_KEY or ""
    model = config.CLAUDE_MODEL

    _insights_job.update(running=True, done=0, total=0, result=None, error="")

    def work():
        try:
            def prog(done, total):
                _insights_job["done"] = done
                _insights_job["total"] = total
            res = analytics.analyze(acc, limit=limit, on_progress=prog,
                                    anthropic_key=akey, model=model)
            _insights_job["result"] = res
            if not res.get("ok"):
                _insights_job["error"] = res.get("error", "")
        except ThreadsError as exc:
            _insights_job["error"] = str(exc)
        except Exception as exc:  # noqa: BLE001
            _insights_job["error"] = str(exc)
        finally:
            _insights_job["running"] = False

    threading.Thread(target=work, daemon=True).start()
    return jsonify({"ok": True, "running": True})


@app.get("/api/insights_status")
def api_insights_status():
    return jsonify({
        "ok": True, "running": _insights_job["running"],
        "done": _insights_job["done"], "total": _insights_job["total"],
        "result": _insights_job["result"], "error": _insights_job["error"],
    })


# ── 예약 발행 (특정 글을 예약 시각에 자동 게시) ──
_publish_watcher = {"started": False}


def _public_sched_item(it: dict) -> dict:
    """UI용: 계정 라벨 붙이고 토큰 등 불필요 정보 제외."""
    all_accs = {a["id"]: a for a in accounts.list_accounts()}
    ids = it.get("account_ids") or []
    labels = [
        (all_accs[i].get("username") and "@" + all_accs[i]["username"])
        or all_accs[i].get("label", "계정")
        for i in ids if i in all_accs
    ] or ["(전체 계정)"]
    return {
        "id": it["id"], "text": it["text"], "run_at": it.get("run_at"),
        "accounts": labels, "status": it.get("status", "pending"),
        "result": it.get("result"),
        "has_media": bool(it.get("image_urls") or it.get("video_url")),
    }


def _scheduled_publish_loop():
    """예약 시각이 된 글을 자동으로 발행하는 워처."""
    from threads_auto import scheduled_posts
    while True:
        try:
            for item in scheduled_posts.due():
                all_accs = accounts.list_accounts()
                ids = item.get("account_ids") or []
                targets = [a for a in all_accs if a["id"] in ids] if ids else all_accs
                if not targets:
                    scheduled_posts.mark(item["id"], "failed", {"summary": "대상 계정이 없어요."})
                    continue
                try:
                    results = _publish(item["text"], item.get("image_urls") or [],
                                       item.get("video_url"), targets, item.get("topic"))
                    success = sum(1 for r in results if r.get("ok"))
                    scheduled_posts.mark(
                        item["id"], "done" if success else "failed",
                        {"summary": f"{success}/{len(results)} 계정 게시", "results": results},
                    )
                except Exception as exc:  # noqa: BLE001
                    scheduled_posts.mark(item["id"], "failed", {"summary": "오류: " + str(exc)})
        except Exception:  # noqa: BLE001
            pass
        for _ in range(30):  # 30초마다 점검
            time.sleep(1)


def _ensure_publish_watcher():
    if _publish_watcher["started"]:
        return
    _publish_watcher["started"] = True
    threading.Thread(target=_scheduled_publish_loop, daemon=True).start()


@app.post("/api/schedule_post")
def api_schedule_post():
    """현재 글을 예약 시각에 발행하도록 큐에 추가합니다."""
    from threads_auto import scheduled_posts
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "예약할 글이 비어 있어요."}), 400
    if len(text) > 500:
        return jsonify({"ok": False, "error": f"글이 너무 길어요({len(text)}자)."}), 400
    run_at = data.get("run_at")
    if not run_at:
        return jsonify({"ok": False, "error": "예약 시각을 골라주세요."}), 400
    run_at = int(run_at)
    if run_at < int(time.time() * 1000) - 60000:
        return jsonify({"ok": False, "error": "과거 시각은 예약할 수 없어요."}), 400

    all_accs = accounts.list_accounts()
    if not all_accs:
        return jsonify({"ok": False, "error": "등록된 계정이 없어요. '계정' 탭에서 추가하세요."}), 400
    acc_ids = data.get("account_ids") or []
    if acc_ids and not any(a["id"] in acc_ids for a in all_accs):
        return jsonify({"ok": False, "error": "게시할 계정을 선택하세요."}), 400

    image_urls = [u for u in (data.get("image_urls") or []) if u]
    video_url = (data.get("video_url") or "").strip() or None
    item = scheduled_posts.add(text, run_at, acc_ids, image_urls, video_url, data.get("topic"))
    _ensure_publish_watcher()
    return jsonify({"ok": True, "item": _public_sched_item(item)})


@app.get("/api/scheduled")
def api_scheduled_list():
    from threads_auto import scheduled_posts
    return jsonify({"ok": True,
                    "items": [_public_sched_item(i) for i in scheduled_posts.list_all()]})


@app.post("/api/scheduled/delete")
def api_scheduled_delete():
    from threads_auto import scheduled_posts
    data = request.get_json(silent=True) or {}
    scheduled_posts.delete((data.get("id") or "").strip())
    return jsonify({"ok": True})


@app.post("/api/scheduled/edit")
def api_scheduled_edit():
    """예약된 글 본문을 수정하고, 수정 내용을 학습합니다(이전 글과 비교)."""
    from threads_auto import scheduled_posts
    data = request.get_json(silent=True) or {}
    item_id = (data.get("id") or "").strip()
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "글이 비어 있어요."}), 400
    res = scheduled_posts.update_text(item_id, text)
    if not res:
        return jsonify({"ok": False, "error": "수정할 수 없는 글이에요(이미 발행됐거나 없음)."}), 400
    # 이전 글과 비교해 학습: 그 예약 글이 묶인 계정(없으면 활성 계정)으로 저장
    acc_ids = res["item"].get("account_ids") or []
    acc_id = acc_ids[0] if acc_ids else (accounts.get_active() or {}).get("id")
    learned = samples.add_edit(acc_id, res["old_text"], text)
    return jsonify({"ok": True, "learned": learned})


@app.post("/api/learn_edit")
def api_learn_edit():
    """글쓰기 칸에서 AI 원본(original)을 사용자가 고친 글(edited)로 바꾼 걸 학습."""
    data = request.get_json(silent=True) or {}
    original = (data.get("original") or "").strip()
    edited = (data.get("edited") or "").strip()
    acc = accounts.get_active()
    acc_id = acc.get("id") if acc else None
    if not acc_id:
        return jsonify({"ok": False, "error": "활성 계정이 없어요. '계정' 탭에서 골라주세요."}), 400
    if not edited:
        return jsonify({"ok": False, "error": "고친 글이 비어 있어요."}), 400
    if original == edited:
        return jsonify({"ok": False, "error": "원본과 똑같아요. 고친 내용이 있어야 학습해요."}), 400
    learned = samples.add_edit(acc_id, original, edited)
    return jsonify({"ok": learned,
                    "error": None if learned else "학습할 차이를 찾지 못했어요."})


# ── 자동 예약 채우기 (현재 계정 말투로 N일치 글 생성 → 매일 예약) ──
_autofill_job = {"running": False, "done": 0, "total": 0, "scheduled": 0, "error": ""}


@app.post("/api/schedule_autofill")
def api_schedule_autofill():
    """현재 계정 말투로 N일치 글을 생성해 매일 1개씩 예약합니다(백그라운드)."""
    if _autofill_job["running"]:
        return jsonify({"ok": True, "running": True, "already": True})
    try:
        config.require_anthropic()
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    acc = accounts.get_active()
    if not acc:
        return jsonify({"ok": False, "error": "연결된 계정이 없어요. '계정' 탭에서 추가하세요."}), 400

    data = request.get_json(silent=True) or {}
    days = max(1, min(30, int(data.get("days", 10))))
    time_str = (data.get("time") or "21:00").strip()
    category = (data.get("category") or "").strip() or None
    auto_time = bool(data.get("auto_time", False))  # AI가 글 읽고 시간 정하기
    try:
        hh, mm = (int(x) for x in time_str.split(":")[:2])
    except Exception:  # noqa: BLE001
        hh, mm = 21, 0

    from datetime import timedelta, datetime as _dt, time as _time
    from threads_auto.content_generator import load_categorized_topics
    from threads_auto import samples, scheduled_posts
    from threads_auto.pipeline import parse_hhmm

    persona = acc.get("persona", "general")
    examples = samples.get_samples(acc["id"], persona, limit=10)
    lessons = samples.get_edit_lessons(acc["id"])
    pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)

    cats = load_categorized_topics()
    pool = list(cats[category]) if (category and category in cats) else \
        [t for items in cats.values() for t in items]
    random.shuffle(pool)

    _autofill_job.update(running=True, done=0, total=days, scheduled=0, error="")

    def work():
        try:
            now = datetime.now()
            day_cursor = now.date()  # 하루에 하나씩 배치할 날짜 커서
            for i in range(days):
                topic = pool[i % len(pool)] if pool else "오늘의 이야기"
                try:
                    res = pipe.run(topic, persona=persona, examples=examples,
                                   category=category or "", edit_lessons=lessons)
                    text = res.get("text", "").strip()
                except Exception:  # noqa: BLE001 (한 개 실패해도 계속)
                    text = ""
                if text:
                    # 시각: AI 자동(글 내용 기반) 또는 사용자가 고른 고정 시각
                    if auto_time:
                        ph, pm = pipe.suggest_time(text)
                    else:
                        ph, pm = hh, mm
                    slot = _dt.combine(day_cursor, _time(ph, pm))
                    if slot <= now + timedelta(minutes=2):
                        day_cursor = day_cursor + timedelta(days=1)
                        slot = _dt.combine(day_cursor, _time(ph, pm))
                    scheduled_posts.add(text, int(slot.timestamp() * 1000),
                                        [acc["id"]], topic=topic)
                    _autofill_job["scheduled"] += 1
                day_cursor = day_cursor + timedelta(days=1)  # 다음 글은 다음 날
                _autofill_job["done"] = i + 1
            _ensure_publish_watcher()
        except Exception as exc:  # noqa: BLE001
            _autofill_job["error"] = str(exc)
        finally:
            _autofill_job["running"] = False

    threading.Thread(target=work, daemon=True).start()
    return jsonify({"ok": True, "running": True})


@app.get("/api/schedule_autofill_status")
def api_schedule_autofill_status():
    return jsonify({"ok": True, "running": _autofill_job["running"],
                    "done": _autofill_job["done"], "total": _autofill_job["total"],
                    "scheduled": _autofill_job["scheduled"], "error": _autofill_job["error"]})


@app.post("/api/suggest_time")
def api_suggest_time():
    """글 내용을 AI가 읽고 어울리는 발행 시각(HH:MM)을 추천합니다."""
    try:
        config.require_anthropic()
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "글이 비어 있어요."}), 400
    try:
        pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)
        h, m = pipe.suggest_time(text)
        return jsonify({"ok": True, "time": f"{h:02d}:{m:02d}"})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500


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
    # 자동 답글이 켜진 계정이 있으면 시작과 동시에 실시간 추적 시작
    _ensure_auto_reply_watcher()
    # 예약 발행 워처도 시작(예약해 둔 글이 시간이 되면 자동 발행)
    _ensure_publish_watcher()
    app.run(host="127.0.0.1", port=port, debug=False)
