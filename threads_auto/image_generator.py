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
IMGUR_UPLOAD_URL = "https://api.imgur.com/3/image"


class ImageError(RuntimeError):
    """이미지 생성/호스팅 실패 시 발생하는 예외."""


def generate_image(api_key: str, prompt: str, model: str = "gpt-image-1",
                   size: str = "1024x1024", timeout: int = 120) -> bytes:
    """OpenAI 이미지 API로 이미지를 생성해 PNG 바이트로 반환합니다."""
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
                          model: str = "gpt-image-1", size: str = "1024x1024") -> str:
    """프롬프트 → AI 이미지 생성 → (Imgur 또는 cloudflared 터널) 호스팅 → 공개 URL.

    Imgur Client-ID가 있으면 Imgur를 쓰고, 없으면 cloudflared 터널로 직접 호스팅합니다.
    """
    image_bytes = generate_image(openai_key, prompt, model=model, size=size)
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
