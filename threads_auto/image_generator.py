"""AI 이미지 생성 + 공개 URL 호스팅.

- 이미지 생성: OpenAI 이미지 API (Claude는 이미지 생성을 못 하므로 별도 서비스 사용)
- 호스팅: Imgur 익명 업로드 (무료, Client-ID 하나만 필요)

Threads API는 '공개적으로 접근 가능한 image_url'만 받기 때문에,
생성한 이미지를 인터넷(Imgur)에 올려 URL을 만든 뒤 그 URL을 게시에 사용합니다.
"""

from __future__ import annotations

import base64

import requests

OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
IMGUR_UPLOAD_URL = "https://api.imgur.com/3/image"


class ImageError(RuntimeError):
    """이미지 생성/호스팅 실패 시 발생하는 예외."""


def generate_image(api_key: str, prompt: str, model: str = "gpt-image-1",
                   size: str = "1024x1024", timeout: int = 120) -> bytes:
    """OpenAI 이미지 API로 이미지를 생성해 PNG 바이트로 반환합니다."""
    api_key = (api_key or "").strip()
    # OpenAI 키는 영문/숫자(ASCII)여야 함. 한글 등이 섞이면 친절히 안내.
    if not api_key.isascii() or not api_key.startswith("sk-"):
        raise ImageError(
            "OpenAI 키 형식이 올바르지 않습니다. .env의 OPENAI_API_KEY에 "
            "한글·공백 없이 'sk-'로 시작하는 키 전체를 넣었는지 확인하세요."
        )
    resp = requests.post(
        OPENAI_IMAGE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "prompt": prompt, "size": size, "n": 1},
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise ImageError(f"이미지 생성 실패 {resp.status_code}: {resp.text[:300]}")

    data = resp.json().get("data", [])
    if not data:
        raise ImageError(f"이미지 응답이 비어 있습니다: {resp.text[:300]}")

    item = data[0]
    # gpt-image-1은 b64_json, DALL·E는 url을 줄 수 있어 둘 다 처리
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        img = requests.get(item["url"], timeout=timeout)
        if img.status_code >= 400:
            raise ImageError(f"생성된 이미지 다운로드 실패 {img.status_code}")
        return img.content
    raise ImageError(f"이미지 데이터를 찾을 수 없습니다: {resp.text[:300]}")


def generate_image_gemini(api_key: str, prompt: str,
                          model: str = "gemini-2.5-flash-image",
                          timeout: int = 120) -> bytes:
    """구글 제미나이 이미지 생성 API로 이미지를 만들어 바이트로 반환합니다.

    키 발급: aistudio.google.com → 'Get API key' (무료 한도 있음)
    """
    api_key = (api_key or "").strip()
    if not api_key:
        raise ImageError("GEMINI_API_KEY가 비어 있습니다.")
    resp = requests.post(
        f"{GEMINI_API_URL}/{model}:generateContent",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        },
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise ImageError(f"제미나이 이미지 생성 실패 {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    for cand in data.get("candidates", []):
        for part in (cand.get("content") or {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data") or {}
            if inline.get("data"):
                return base64.b64decode(inline["data"])
    raise ImageError(f"제미나이 응답에 이미지가 없습니다: {str(data)[:300]}")


def generate_image_any(prompt: str, openai_key: str = "", gemini_key: str = "",
                       openai_model: str = "gpt-image-1",
                       gemini_model: str = "gemini-2.5-flash-image",
                       size: str = "1024x1024") -> bytes:
    """가능한 백엔드로 이미지 생성. 제미나이 우선, 실패하면 OpenAI 폴백."""
    errors = []
    if gemini_key:
        try:
            return generate_image_gemini(gemini_key, prompt, model=gemini_model)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"제미나이: {exc}")
    if openai_key:
        try:
            return generate_image(openai_key, prompt, model=openai_model, size=size)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"OpenAI: {exc}")
    if errors:
        raise ImageError(" / ".join(errors))
    raise ImageError("이미지 생성 키가 없습니다. .env에 GEMINI_API_KEY(추천) "
                     "또는 OPENAI_API_KEY를 넣으세요.")


def upload_to_imgur(client_id: str, image_bytes: bytes, timeout: int = 60) -> str:
    """이미지를 Imgur에 익명 업로드하고 공개 URL을 반환합니다."""
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    resp = requests.post(
        IMGUR_UPLOAD_URL,
        headers={"Authorization": f"Client-ID {client_id}"},
        data={"image": b64, "type": "base64"},
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise ImageError(f"Imgur 업로드 실패 {resp.status_code}: {resp.text[:300]}")
    link = resp.json().get("data", {}).get("link")
    if not link:
        raise ImageError(f"Imgur가 URL을 주지 않았습니다: {resp.text[:300]}")
    return link


def create_image_url(openai_key: str, imgur_client_id: str, prompt: str,
                     model: str = "gpt-image-1", size: str = "1024x1024") -> str:
    """프롬프트 → AI 이미지 생성 → Imgur 업로드 → 공개 URL 반환 (한 번에)."""
    image_bytes = generate_image(openai_key, prompt, model=model, size=size)
    return upload_to_imgur(imgur_client_id, image_bytes)


def create_image_url_auto(openai_key: str, imgur_client_id: str, prompt: str,
                          model: str = "gpt-image-1", size: str = "1024x1024",
                          gemini_key: str = "",
                          gemini_model: str = "gemini-2.5-flash-image") -> str:
    """프롬프트 → AI 이미지 생성(제미나이 우선) → (Imgur 또는 터널) 호스팅 → 공개 URL.

    Imgur Client-ID가 있으면 Imgur를 쓰고, 없으면 cloudflared 터널로 직접 호스팅합니다.
    """
    image_bytes = generate_image_any(prompt, openai_key=openai_key,
                                     gemini_key=gemini_key, openai_model=model,
                                     gemini_model=gemini_model, size=size)
    if imgur_client_id:
        return upload_to_imgur(imgur_client_id, image_bytes)

    # Imgur 키가 없으면 터널로 직접 호스팅
    from threads_auto import tunnel_host

    try:
        return tunnel_host.host_image(image_bytes)
    except tunnel_host.TunnelError as exc:
        raise ImageError(
            f"이미지 호스팅 실패(터널): {exc}. cloudflared 설치 또는 IMGUR_CLIENT_ID를 확인하세요."
        ) from exc
