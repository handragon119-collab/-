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


def publish_carousel(image_paths: list[str], caption: str, config: Config) -> str:
    """여러 이미지를 하나의 캐러셀(슬라이드) 게시물로 업로드한다."""
    method = config.publisher
    if method == "none":
        return f"업로드 건너뜀 (PUBLISHER=none, 슬라이드 {len(image_paths)}장)"
    if method == "instagrapi":
        return _carousel_instagrapi(image_paths, caption, config)
    if method == "graph":
        return _carousel_graph(image_paths, caption, config)
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

    # 로컬 이미지를 공개 URL로 호스팅 (imgbb 등) → Graph API가 가져갈 수 있게 함
    from .image_host import to_public_url

    image_url = to_public_url(image_path, config)
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
    _graph_wait(creation_id, token)

    # 3) 게시
    publish_res = requests.post(
        f"{api}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    ).json()
    if "id" not in publish_res:
        raise RuntimeError(f"게시 실패: {publish_res}")
    return f"Graph API 업로드 완료 (media id={publish_res['id']})"


def _graph_wait(creation_id: str, token: str) -> None:
    """컨테이너 처리(FINISHED)까지 대기."""
    for _ in range(30):
        status = requests.get(
            f"https://graph.facebook.com/v21.0/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        ).json()
        if status.get("status_code") == "FINISHED":
            return
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"컨테이너 처리 오류: {status}")
        time.sleep(3)


# --------------------------------------------------------------------------- #
# 캐러셀(여러 장) 업로드 - 카드뉴스용
# --------------------------------------------------------------------------- #
def _carousel_graph(image_paths: list[str], caption: str, config: Config) -> str:
    config.require("ig_graph_access_token", "ig_graph_user_id")
    from .image_host import to_public_url

    api = f"https://graph.facebook.com/v21.0/{config.ig_graph_user_id}"
    token = config.ig_graph_access_token

    # 1) 각 슬라이드를 캐러셀 아이템 컨테이너로 생성
    child_ids = []
    for path in image_paths:
        image_url = to_public_url(path, config)
        res = requests.post(
            f"{api}/media",
            data={
                "image_url": image_url,
                "is_carousel_item": "true",
                "access_token": token,
            },
            timeout=60,
        ).json()
        if "id" not in res:
            raise RuntimeError(f"슬라이드 컨테이너 생성 실패: {res}")
        child_ids.append(res["id"])

    # 2) 부모 캐러셀 컨테이너 생성
    parent = requests.post(
        f"{api}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": token,
        },
        timeout=60,
    ).json()
    if "id" not in parent:
        raise RuntimeError(f"캐러셀 컨테이너 생성 실패: {parent}")
    _graph_wait(parent["id"], token)

    # 3) 게시
    pub = requests.post(
        f"{api}/media_publish",
        data={"creation_id": parent["id"], "access_token": token},
        timeout=60,
    ).json()
    if "id" not in pub:
        raise RuntimeError(f"캐러셀 게시 실패: {pub}")
    return f"Graph API 캐러셀 업로드 완료 ({len(image_paths)}장, media id={pub['id']})"


def _carousel_instagrapi(image_paths: list[str], caption: str, config: Config) -> str:
    config.require("ig_username", "ig_password")
    try:
        from instagrapi import Client
    except ImportError as e:
        raise RuntimeError("instagrapi 패키지가 필요합니다: pip install instagrapi") from e

    cl = Client()
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

    media = cl.album_upload([str(p) for p in image_paths], caption)
    return f"instagrapi 캐러셀 업로드 완료 ({len(image_paths)}장, pk={media.pk})"
