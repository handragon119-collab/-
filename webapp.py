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
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import config
import random

from threads_auto import safety
from threads_auto import accounts
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

    persona, examples, _ = _active_persona()
    try:
        if advanced and topic:
            pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)
            result = pipe.run(topic, persona=persona, examples=examples)
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

    persona, examples, _ = _active_persona()
    pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)
    meta = None
    try:
        if advanced and topic:
            result = pipe.run(topic, persona=persona, examples=examples)
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

    try:
        if is_video:
            f = files[0]
            data = f.read()
            if len(data) > 100 * 1024 * 1024:
                return jsonify({"ok": False, "error": "영상이 너무 큽니다(100MB 이하)."}), 400
            video_url = _host_bytes(data, first_ext)
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
                image_urls.append(_host_bytes(data, ext))
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
                    "topic": data.get("topic"),
                    "text": text,
                    "post_id": post_id,
                    "image_urls": image_urls,
                    "video_url": video_url,
                }, ensure_ascii=False) + "\n")
        except ThreadsError as exc:
            results.append({"label": a["label"], "ok": False, "error": str(exc)})
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
    app.run(host="127.0.0.1", port=port, debug=False)
