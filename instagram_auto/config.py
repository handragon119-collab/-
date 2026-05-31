"""환경변수 기반 설정 로더."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv 미설치 시에도 동작 (시스템 환경변수 사용)
    pass


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass
class Config:
    """프로그램 전체 설정. 환경변수(.env)에서 로드된다."""

    # 캡션 생성 제공자: anthropic | gemini
    caption_provider: str = field(
        default_factory=lambda: _get("CAPTION_PROVIDER", "anthropic").lower()
    )
    anthropic_api_key: str = field(default_factory=lambda: _get("ANTHROPIC_API_KEY"))
    caption_model: str = field(
        default_factory=lambda: _get("CAPTION_MODEL", "claude-sonnet-4-6")
    )
    # Gemini 캡션용 텍스트 모델 (무료 등급 가능)
    gemini_text_model: str = field(
        default_factory=lambda: _get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
    )

    # 이미지 생성
    image_provider: str = field(
        default_factory=lambda: _get("IMAGE_PROVIDER", "placeholder").lower()
    )
    openai_api_key: str = field(default_factory=lambda: _get("OPENAI_API_KEY"))
    openai_image_model: str = field(
        default_factory=lambda: _get("OPENAI_IMAGE_MODEL", "gpt-image-1")
    )
    gemini_api_key: str = field(default_factory=lambda: _get("GEMINI_API_KEY"))
    gemini_image_model: str = field(
        default_factory=lambda: _get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    )
    # 인스타그램 피드 기본은 정사각형(1:1)
    image_aspect_ratio: str = field(
        default_factory=lambda: _get("IMAGE_ASPECT_RATIO", "1:1")
    )
    # Pollinations(무료) 선택적 토큰 - 없어도 동작
    pollinations_token: str = field(
        default_factory=lambda: _get("POLLINATIONS_TOKEN")
    )

    # 인스타그램 업로드
    publisher: str = field(default_factory=lambda: _get("PUBLISHER", "none").lower())
    ig_username: str = field(default_factory=lambda: _get("IG_USERNAME"))
    ig_password: str = field(default_factory=lambda: _get("IG_PASSWORD"))
    ig_graph_access_token: str = field(
        default_factory=lambda: _get("IG_GRAPH_ACCESS_TOKEN")
    )
    ig_graph_user_id: str = field(default_factory=lambda: _get("IG_GRAPH_USER_ID"))
    public_image_base_url: str = field(
        default_factory=lambda: _get("PUBLIC_IMAGE_BASE_URL")
    )
    # Graph API용 공개 URL 생성 방식: imgbb | cloudinary | base_url
    image_host: str = field(default_factory=lambda: _get("IMAGE_HOST", "imgbb").lower())
    imgbb_api_key: str = field(default_factory=lambda: _get("IMGBB_API_KEY"))

    # 출력 디렉터리
    output_dir: str = field(default_factory=lambda: _get("OUTPUT_DIR", "output"))

    def require(self, *names: str) -> None:
        """필수 설정값이 비어있으면 친절한 에러를 발생시킨다."""
        missing = [n for n in names if not getattr(self, n)]
        if missing:
            raise RuntimeError(
                "다음 환경변수가 필요합니다: "
                + ", ".join(n.upper() for n in missing)
                + " (.env 파일을 확인하세요)"
            )
