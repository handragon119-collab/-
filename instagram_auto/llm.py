"""LLM 텍스트 생성 공통 모듈 (캡션/카드뉴스 내용 공용).

CAPTION_PROVIDER 에 따라 Claude 또는 Gemini(무료 등급)를 사용한다.
"""

from __future__ import annotations

import json

from .config import Config


def complete(system: str, user_prompt: str, config: Config) -> str:
    """system + user 프롬프트로 모델을 호출해 텍스트를 반환한다."""
    provider = config.caption_provider
    if provider == "anthropic":
        return _anthropic(system, user_prompt, config)
    if provider == "gemini":
        return _gemini(system, user_prompt, config)
    raise RuntimeError(f"알 수 없는 CAPTION_PROVIDER: {provider}")


def complete_json(system: str, user_prompt: str, config: Config) -> dict:
    """모델 응답을 JSON 객체로 파싱해 반환한다."""
    return parse_json(complete(system, user_prompt, config))


def _anthropic(system: str, user_prompt: str, config: Config) -> str:
    config.require("anthropic_api_key")
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("anthropic 패키지가 필요합니다: pip install anthropic") from e

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    message = client.messages.create(
        model=config.caption_model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(b.text for b in message.content if b.type == "text")


def _gemini(system: str, user_prompt: str, config: Config) -> str:
    config.require("gemini_api_key")
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError("google-genai 패키지가 필요합니다: pip install google-genai") from e

    client = genai.Client(api_key=config.gemini_api_key)
    response = client.models.generate_content(
        model=config.gemini_text_model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
        ),
    )
    return response.text or ""


def parse_json(raw: str) -> dict:
    """모델 응답에서 JSON 객체를 안전하게 추출한다."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start : end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM JSON 파싱 실패: {e}\n원본: {raw[:300]}") from e
