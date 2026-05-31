"""한글 폰트 로더.

카드뉴스는 한글 렌더링이 핵심이라 제대로 된 한글 폰트가 필요하다.
나눔고딕을 캐시 디렉터리에 자동 다운로드하고, 실패 시 시스템 CJK 폰트로 폴백한다.
FONT_DIR 환경변수로 직접 폰트 폴더를 지정할 수도 있다.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
from PIL import ImageFont

_BASE = "https://github.com/google/fonts/raw/main/ofl/nanumgothic"
_BASE_SERIF = "https://github.com/google/fonts/raw/main/ofl/nanummyeongjo"
_FILES = {
    "regular": ("NanumGothic-Regular.ttf", _BASE),
    "bold": ("NanumGothic-Bold.ttf", _BASE),
    "extrabold": ("NanumGothic-ExtraBold.ttf", _BASE),
    # 고급/편집 디자인용 명조(serif)
    "serif": ("NanumMyeongjo-Bold.ttf", _BASE_SERIF),
    "serif_xb": ("NanumMyeongjo-ExtraBold.ttf", _BASE_SERIF),
}

# 다운로드 실패 시 폴백할 시스템 CJK 폰트 후보
_SYSTEM_FALLBACKS = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # macOS
    "C:/Windows/Fonts/malgun.ttf",  # Windows 맑은고딕
]

_cache_dir = Path(os.environ.get("FONT_DIR", "")) or (
    Path.home() / ".cache" / "instagram_auto" / "fonts"
)


def _ensure(weight: str) -> str | None:
    """해당 두께 폰트 파일 경로를 확보(필요 시 다운로드)해 반환."""
    fname, base = _FILES.get(weight, _FILES["regular"])
    path = _cache_dir / fname
    if path.exists() and path.stat().st_size > 10000:
        return str(path)
    # FONT_DIR 지정 시 다운로드하지 않고 그 안에서만 찾는다
    if os.environ.get("FONT_DIR"):
        return str(path) if path.exists() else None
    try:
        _cache_dir.mkdir(parents=True, exist_ok=True)
        resp = requests.get(f"{base}/{fname}", timeout=60)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        return str(path)
    except Exception:
        return None


def get_font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    """크기와 두께(regular/bold/extrabold)에 맞는 폰트를 반환한다."""
    path = _ensure(weight)
    if path:
        return ImageFont.truetype(path, size)
    for fb in _SYSTEM_FALLBACKS:
        if Path(fb).exists():
            return ImageFont.truetype(fb, size)
    # 최후의 폴백 (한글은 깨질 수 있음)
    return ImageFont.load_default()
