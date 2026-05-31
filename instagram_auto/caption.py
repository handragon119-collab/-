"""인스타그램 캡션·해시태그·이미지 프롬프트 생성.

캡션 생성 제공자(CAPTION_PROVIDER):
  - anthropic : Claude (유료, 고품질)
  - gemini    : Gemini 2.5 Flash (무료 등급 가능)
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .config import Config

# 모델에게 JSON 으로만 답하도록 요청한다.
_SYSTEM = """너는 인스타그램 콘텐츠 전문 카피라이터다.
주어진 주제로 매력적인 인스타그램 게시물을 기획한다.
반드시 아래 JSON 형식으로만 답하라. 다른 설명은 절대 붙이지 마라.

{
  "caption": "사람의 감정을 끄는 2~4문장의 한국어 캡션. 적절한 이모지 포함.",
  "hashtags": ["#태그1", "#태그2", ... 12~20개, 한국어/영어 혼합, # 포함],
  "image_prompt": "이미지 생성 AI에게 줄 영어 프롬프트. 사진처럼 구체적이고 시각적으로. 텍스트/글자는 넣지 말 것."
}"""

_USER_TEMPLATE = """주제: {topic}

톤앤매너: {tone}
이 주제로 인스타그램 게시물 1개를 기획해줘."""


@dataclass
class CaptionResult:
    caption: str
    hashtags: list[str]
    image_prompt: str

    @property
    def full_text(self) -> str:
        """캡션 + 해시태그를 합친 최종 게시 텍스트."""
        tags = " ".join(self.hashtags)
        return f"{self.caption}\n\n{tags}".strip()


def generate_caption(topic: str, config: Config, tone: str = "친근하고 감성적인") -> CaptionResult:
    """주제로부터 캡션/해시태그/이미지 프롬프트를 생성한다."""
    user_prompt = _USER_TEMPLATE.format(topic=topic, tone=tone)

    provider = config.caption_provider
    if provider == "anthropic":
        raw = _anthropic(user_prompt, config)
    elif provider == "gemini":
        raw = _gemini(user_prompt, config)
    else:
        raise RuntimeError(f"알 수 없는 CAPTION_PROVIDER: {provider}")

    data = _parse_json(raw)
    hashtags = [_normalize_tag(t) for t in data.get("hashtags", []) if t.strip()]
    return CaptionResult(
        caption=data.get("caption", "").strip(),
        hashtags=hashtags,
        image_prompt=data.get("image_prompt", topic).strip(),
    )


def _anthropic(user_prompt: str, config: Config) -> str:
    config.require("anthropic_api_key")
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("anthropic 패키지가 필요합니다: pip install anthropic") from e

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    message = client.messages.create(
        model=config.caption_model,
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def _gemini(user_prompt: str, config: Config) -> str:
    """Gemini 2.5 Flash로 캡션 생성 (무료 등급 사용 가능)."""
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
            system_instruction=_SYSTEM,
            response_mime_type="application/json",
        ),
    )
    return response.text or ""


def _normalize_tag(tag: str) -> str:
    tag = tag.strip().replace(" ", "")
    return tag if tag.startswith("#") else f"#{tag}"


def _parse_json(raw: str) -> dict:
    """모델 응답에서 JSON 객체를 안전하게 추출한다."""
    raw = raw.strip()
    # 코드펜스 제거
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
        raise RuntimeError(f"캡션 응답 파싱 실패: {e}\n원본: {raw[:300]}") from e
