"""웹 UI용 설정 저장/로드 및 Config 빌더.

자격증명은 프로젝트 루트의 web_settings.json 에 저장한다(.gitignore 처리).
이 파일은 로컬 전용이며, 공개 서버에 배포할 때는 반드시 인증을 추가해야 한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from instagram_auto.config import Config

SETTINGS_PATH = Path("web_settings.json")

# UI에서 다루는 설정 키 (Config 속성명과 일치)
FIELDS = [
    "caption_provider", "anthropic_api_key", "caption_model",
    "gemini_api_key", "gemini_text_model",
    "content_mode", "card_count", "card_theme", "card_size", "brand_handle",
    "publisher", "ig_graph_access_token", "ig_graph_user_id",
    "image_host", "imgbb_api_key", "public_image_base_url",
    "image_provider",
]
SECRET_FIELDS = {
    "anthropic_api_key", "gemini_api_key", "ig_graph_access_token", "imgbb_api_key",
}
INT_FIELDS = {"card_count"}


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_settings(updates: dict) -> dict:
    """기존 설정에 병합 저장. 빈 비밀값은 기존 값을 유지."""
    current = load_settings()
    for k, v in updates.items():
        if k not in FIELDS:
            continue
        if k in SECRET_FIELDS and (v is None or v == "" or v == "********"):
            continue  # 비밀값은 비어있으면 기존 유지
        if k in INT_FIELDS:
            try:
                v = int(v)
            except (TypeError, ValueError):
                continue
        current[k] = v
    SETTINGS_PATH.write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return current


def masked_settings() -> dict:
    """UI 표시용. 비밀값은 설정 여부만 알리고 가린다."""
    s = load_settings()
    out = {}
    for k in FIELDS:
        v = s.get(k, "")
        if k in SECRET_FIELDS:
            out[k] = "********" if v else ""
        else:
            out[k] = v
    return out


def build_config(overrides: dict | None = None) -> Config:
    """환경변수 < 저장된 설정 < 요청 오버라이드 순으로 Config를 구성."""
    cfg = Config()
    merged = load_settings()
    if overrides:
        merged = {**merged, **{k: v for k, v in overrides.items() if v not in (None, "")}}
    for k, v in merged.items():
        if not hasattr(cfg, k):
            continue
        if k in INT_FIELDS:
            try:
                v = int(v)
            except (TypeError, ValueError):
                continue
        if v in (None, ""):
            continue
        setattr(cfg, k, v)
    return cfg
