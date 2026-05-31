"""인스타그램 자동발행 웹 서버 (FastAPI).

실행:
    python -m web.server
    # 또는: uvicorn web.server:app --reload
브라우저에서 http://localhost:8000 접속.

⚠️ 로컬 전용. 자격증명을 다루므로 공개 인터넷에 그대로 노출하지 마세요.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from instagram_auto import card_render, content as content_mod  # noqa: E402
from instagram_auto.caption import generate_caption  # noqa: E402
from instagram_auto.image_gen import generate_image  # noqa: E402
from instagram_auto.publisher import publish, publish_carousel  # noqa: E402
from web import settings as settings_mod  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="인스타 자동발행 스튜디오")

# 생성된 콘텐츠를 발행 전까지 보관 (메모리)
JOBS: dict[str, dict] = {}


# --------------------------------------------------------------------------- #
# 요청 모델
# --------------------------------------------------------------------------- #
class GenerateReq(BaseModel):
    topic: str
    mode: str = "cardnews"
    theme: str = "navy"
    cards: int = 6
    tone: str | None = None
    brand_handle: str | None = None
    agentic: bool = False
    number: int | None = None
    kicker: str | None = None


class PublishReq(BaseModel):
    job_id: str
    caption: str | None = None


class SettingsReq(BaseModel):
    data: dict


# --------------------------------------------------------------------------- #
# 설정 / 계정
# --------------------------------------------------------------------------- #
@app.get("/api/settings")
def get_settings():
    return settings_mod.masked_settings()


@app.post("/api/settings")
def post_settings(req: SettingsReq):
    settings_mod.save_settings(req.data)
    return {"ok": True}


@app.get("/api/test-connection")
def test_connection():
    """저장된 설정으로 인스타 계정 연결을 확인한다."""
    cfg = settings_mod.build_config()
    if cfg.publisher == "graph":
        if not (cfg.ig_graph_access_token and cfg.ig_graph_user_id):
            raise HTTPException(400, "Graph API 토큰/계정 ID가 설정되지 않았습니다.")
        try:
            r = requests.get(
                f"https://graph.facebook.com/v21.0/{cfg.ig_graph_user_id}",
                params={
                    "fields": "username,followers_count,media_count",
                    "access_token": cfg.ig_graph_access_token,
                },
                timeout=20,
            ).json()
        except Exception as e:
            raise HTTPException(502, f"연결 오류: {e}")
        if "error" in r:
            raise HTTPException(400, f"연결 실패: {r['error'].get('message', r['error'])}")
        return {
            "ok": True, "method": "graph",
            "username": r.get("username"),
            "followers": r.get("followers_count"),
            "media_count": r.get("media_count"),
        }
    if cfg.publisher == "instagrapi":
        return {"ok": True, "method": "instagrapi",
                "note": "아이디/비밀번호 방식은 실제 발행 시 로그인됩니다."}
    return {"ok": False, "method": cfg.publisher,
            "note": "PUBLISHER가 graph 또는 instagrapi가 아닙니다."}


# --------------------------------------------------------------------------- #
# 콘텐츠 생성 / 발행
# --------------------------------------------------------------------------- #
@app.post("/api/generate")
def api_generate(req: GenerateReq):
    overrides = {
        "content_mode": req.mode,
        "card_theme": req.theme,
        "card_count": req.cards,
    }
    if req.brand_handle is not None:
        overrides["brand_handle"] = req.brand_handle
    if req.agentic:
        overrides["content_engine"] = "agentic"
    cfg = settings_mod.build_config(overrides)

    job_id = uuid.uuid4().hex[:12]
    base = OUTPUT_DIR / f"web_{job_id}"
    agent_report = None

    try:
        if req.mode == "photo":
            cap = generate_caption(req.topic, cfg, tone=req.tone or "친근하고 감성적인")
            img = generate_image(cap.image_prompt, cfg, f"{base}.jpg")
            paths = [img]
            caption, hashtags, cover_title = cap.caption, cap.hashtags, req.topic
        else:
            if cfg.content_engine == "agentic":
                from instagram_auto.agents import generate_cardnews_agentic
                cn, report = generate_cardnews_agentic(
                    req.topic, cfg, tone=req.tone or "친근하고 신뢰감 있는")
                agent_report = {
                    "web_search_used": report.web_search_used,
                    "sources": report.sources, "risk_flags": report.risk_flags,
                    "steps": [s["agent"] for s in report.steps],
                }
            else:
                cn = content_mod.generate_cardnews(
                    req.topic, cfg, tone=req.tone or "친근하고 신뢰감 있는")
            paths = card_render.render_cardnews(
                cn, cfg, str(base), number=req.number, kicker=req.kicker or None)
            caption, hashtags, cover_title = cn.caption, cn.hashtags, cn.cover_title
    except Exception as e:
        raise HTTPException(400, f"생성 실패: {e}")

    full_text = (caption + "\n\n" + " ".join(hashtags)).strip()
    JOBS[job_id] = {
        "image_paths": [str(p) for p in paths],
        "caption": caption, "hashtags": hashtags, "full_text": full_text,
        "topic": req.topic, "mode": req.mode,
    }
    return {
        "job_id": job_id,
        "mode": req.mode,
        "cover_title": cover_title,
        "caption": caption,
        "hashtags": hashtags,
        "full_text": full_text,
        "images": [f"/output/{Path(p).name}" for p in paths],
        "agent_report": agent_report,
    }


@app.post("/api/publish")
def api_publish(req: PublishReq):
    job = JOBS.get(req.job_id)
    if not job:
        raise HTTPException(404, "만료되었거나 존재하지 않는 작업입니다. 다시 생성해주세요.")
    cfg = settings_mod.build_config()
    if cfg.publisher not in ("graph", "instagrapi"):
        raise HTTPException(400, "발행 방식(PUBLISHER)이 설정되지 않았습니다. 계정 연결을 먼저 해주세요.")

    caption = req.caption if req.caption is not None else job["full_text"]
    paths = job["image_paths"]
    try:
        if len(paths) > 1:
            result = publish_carousel(paths, caption, cfg)
        else:
            result = publish(paths[0], caption, cfg)
    except Exception as e:
        raise HTTPException(400, f"발행 실패: {e}")
    return {"ok": True, "result": result}


# --------------------------------------------------------------------------- #
# 정적 파일 / UI
# --------------------------------------------------------------------------- #
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn

    print("➡  http://localhost:8000  접속")
    uvicorn.run(app, host="0.0.0.0", port=8000)
