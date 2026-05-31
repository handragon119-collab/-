"""로컬 이미지를 공개 URL로 만들어주는 호스팅 모듈.

Instagram Graph API는 로컬 파일을 직접 받지 못하고 '인터넷에서 접근 가능한
이미지 URL'을 요구한다. 이 모듈이 생성된 이미지를 업로드해 그 URL을 돌려준다.

지원 방식 (IMAGE_HOST):
  - imgbb      : 무료 이미지 호스팅. IMGBB_API_KEY 하나만 필요. (기본/추천)
  - cloudinary : Cloudinary 미디어 CDN.
  - base_url   : 이미 공개된 서버/S3가 있어 PUBLIC_IMAGE_BASE_URL로 접근 가능한 경우.
"""

from __future__ import annotations

import base64
import os

import requests

from .config import Config


def to_public_url(image_path: str, config: Config) -> str:
    """이미지 파일을 공개적으로 접근 가능한 URL로 변환해 반환한다."""
    host = config.image_host
    if host == "imgbb":
        return _imgbb(image_path, config)
    if host == "cloudinary":
        return _cloudinary(image_path, config)
    if host == "base_url":
        return _base_url(image_path, config)
    raise RuntimeError(f"알 수 없는 IMAGE_HOST: {host}")


# --------------------------------------------------------------------------- #
# imgbb (무료, API 키 하나)
# --------------------------------------------------------------------------- #
def _imgbb(image_path: str, config: Config) -> str:
    config.require("imgbb_api_key")
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read())

    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": config.imgbb_api_key, "image": encoded},
        timeout=60,
    )
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"imgbb 업로드 실패: {data}")
    # Graph API가 바로 가져갈 수 있는 직접 이미지 URL
    return data["data"]["url"]


# --------------------------------------------------------------------------- #
# Cloudinary
# --------------------------------------------------------------------------- #
def _cloudinary(image_path: str, config: Config) -> str:
    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError as e:
        raise RuntimeError("cloudinary 패키지가 필요합니다: pip install cloudinary") from e

    # cloudinary는 자체 환경변수(CLOUDINARY_URL) 또는 개별 키를 사용
    result = cloudinary.uploader.upload(image_path)
    return result["secure_url"]


# --------------------------------------------------------------------------- #
# 이미 공개된 서버/S3
# --------------------------------------------------------------------------- #
def _base_url(image_path: str, config: Config) -> str:
    if not config.public_image_base_url:
        raise RuntimeError("PUBLIC_IMAGE_BASE_URL 이 설정되지 않았습니다.")
    base = config.public_image_base_url.rstrip("/")
    return f"{base}/{os.path.basename(image_path)}"
