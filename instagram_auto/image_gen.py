"""AI 이미지 생성 모듈 (제공자 플러그인 방식).

지원 제공자:
  - openai      : DALL·E 3 / gpt-image-1
  - gemini      : Google Gemini 이미지 생성
  - placeholder : API 키 없이도 동작하는 로컬 PIL 카드 (테스트/오프라인용)
"""

from __future__ import annotations

import base64
import os
import textwrap
from pathlib import Path

import requests

from .config import Config


def generate_image(prompt: str, config: Config, out_path: str) -> str:
    """프롬프트로 이미지를 생성하고 out_path 에 저장한 뒤 경로를 반환한다."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    provider = config.image_provider

    if provider == "openai":
        return _openai(prompt, config, out_path)
    if provider == "gemini":
        return _gemini(prompt, config, out_path)
    if provider == "placeholder":
        return _placeholder(prompt, out_path)
    raise RuntimeError(f"알 수 없는 IMAGE_PROVIDER: {provider}")


# --------------------------------------------------------------------------- #
# OpenAI (DALL·E 3 / gpt-image-1)
# --------------------------------------------------------------------------- #
def _openai(prompt: str, config: Config, out_path: str) -> str:
    config.require("openai_api_key")
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("openai 패키지가 필요합니다: pip install openai") from e

    client = OpenAI(api_key=config.openai_api_key)
    result = client.images.generate(
        model=config.openai_image_model,
        prompt=prompt,
        size="1024x1024",
        n=1,
    )
    item = result.data[0]
    if getattr(item, "b64_json", None):
        _write_bytes(out_path, base64.b64decode(item.b64_json))
    else:  # dall-e-3 는 URL 반환
        _write_bytes(out_path, requests.get(item.url, timeout=60).content)
    return out_path


# --------------------------------------------------------------------------- #
# Google Gemini (gemini-2.5-flash-image / "Nano Banana", 신 google-genai SDK)
# --------------------------------------------------------------------------- #
def _gemini(prompt: str, config: Config, out_path: str) -> str:
    config.require("gemini_api_key")
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError(
            "google-genai 패키지가 필요합니다: pip install google-genai"
        ) from e

    client = genai.Client(api_key=config.gemini_api_key)
    response = client.models.generate_content(
        model=config.gemini_image_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=config.image_aspect_ratio),
        ),
    )

    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        for part in cand.content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                _write_bytes(out_path, inline.data)
                return out_path
    raise RuntimeError(
        "Gemini 응답에 이미지 데이터가 없습니다. (프롬프트가 정책에 막혔거나 모델명이 잘못되었을 수 있습니다)"
    )


# --------------------------------------------------------------------------- #
# 로컬 폴백 (API 키 불필요)
# --------------------------------------------------------------------------- #
def _placeholder(prompt: str, out_path: str) -> str:
    """API 키 없이도 파이프라인 전체를 테스트할 수 있는 텍스트 카드 이미지."""
    from PIL import Image, ImageDraw

    w, h = 1080, 1080
    img = Image.new("RGB", (w, h), (24, 24, 36))
    draw = ImageDraw.Draw(img)

    # 그라데이션 느낌의 배경 막대
    for i in range(0, h, 4):
        shade = 24 + int(60 * (i / h))
        draw.line([(0, i), (w, i)], fill=(shade, 20, 60 + shade // 2))

    text = textwrap.fill(prompt, width=28)[:400]
    draw.multiline_text(
        (60, 80), "AI PLACEHOLDER", fill=(255, 255, 255), spacing=8
    )
    draw.multiline_text((60, 180), text, fill=(235, 235, 245), spacing=14)
    img.save(out_path, "JPEG", quality=90)
    return out_path


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)
