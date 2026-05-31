"""인스타그램 업로드 모듈 (방식 플러그인).

지원 방식:
  - instagrapi : 일반 개인 계정 (아이디/비밀번호). 비공식 API.
  - graph      : 비즈니스/크리에이터 계정. 공식 Instagram Graph API.
  - none       : 업로드하지 않음 (이미지/캡션 생성만).
"""

from __future__ import annotations

import time

import requests

from .config import Config


def publish(image_path: str, caption: str, config: Config) -> str:
    """이미지와 캡션을 업로드하고 결과 메시지(또는 미디어 ID)를 반환한다."""
    method = config.publisher
    if method == "none":
        return "업로드 건너뜀 (PUBLISHER=none)"
    if method == "instagrapi":
        return _via_instagrapi(image_path, caption, config)
    if method == "graph":
        return _via_graph(image_path, caption, config)
    raise RuntimeError(f"알 수 없는 PUBLISHER: {method}")


# --------------------------------------------------------------------------- #
# instagrapi (개인 계정)
# --------------------------------------------------------------------------- #
def _via_instagrapi(image_path: str, caption: str, config: Config) -> str:
    config.require("ig_username", "ig_password")
    try:
        from instagrapi import Client
    except ImportError as e:
        raise RuntimeError("instagrapi 패키지가 필요합니다: pip install instagrapi") from e

    cl = Client()
    # 세션 재사용으로 잦은 로그인(차단 위험)을 줄인다.
    session_file = f"{config.output_dir}/ig_session_{config.ig_username}.json"
    try:
        cl.load_settings(session_file)
        cl.login(config.ig_username, config.ig_password)
    except Exception:
        cl.login(config.ig_username, config.ig_password)
    try:
        cl.dump_settings(session_file)
    except Exception:
        pass

    media = cl.photo_upload(image_path, caption)
    return f"instagrapi 업로드 완료 (media pk={media.pk})"


# --------------------------------------------------------------------------- #
# Instagram Graph API (비즈니스 계정)
# --------------------------------------------------------------------------- #
def _via_graph(image_path: str, caption: str, config: Config) -> str:
    config.require("ig_graph_access_token", "ig_graph_user_id")
    if not config.public_image_base_url:
        raise RuntimeError(
            "Graph API 는 공개 이미지 URL 이 필요합니다. PUBLIC_IMAGE_BASE_URL 을 설정하거나 "
            "이미지를 공개 스토리지(S3 등)에 올린 뒤 그 URL을 사용하세요."
        )

    base = config.public_image_base_url.rstrip("/")
    image_url = f"{base}/{image_path.split('/')[-1]}"
    api = f"https://graph.facebook.com/v21.0/{config.ig_graph_user_id}"
    token = config.ig_graph_access_token

    # 1) 미디어 컨테이너 생성
    create = requests.post(
        f"{api}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=60,
    ).json()
    if "id" not in create:
        raise RuntimeError(f"컨테이너 생성 실패: {create}")
    creation_id = create["id"]

    # 2) 처리 완료까지 대기
    for _ in range(20):
        status = requests.get(
            f"https://graph.facebook.com/v21.0/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        ).json()
        if status.get("status_code") == "FINISHED":
            break
        time.sleep(3)

    # 3) 게시
    publish_res = requests.post(
        f"{api}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    ).json()
    if "id" not in publish_res:
        raise RuntimeError(f"게시 실패: {publish_res}")
    return f"Graph API 업로드 완료 (media id={publish_res['id']})"
