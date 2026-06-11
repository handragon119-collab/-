"""환경 변수를 읽어 설정값을 한곳에서 관리합니다."""

import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("여기에"):
        raise RuntimeError(
            f"환경 변수 {name} 이(가) 설정되지 않았습니다. .env 파일을 확인하세요."
        )
    return value


# Threads (Meta) 공식 API
THREADS_USER_ID = os.getenv("THREADS_USER_ID", "").strip()
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN", "").strip()

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-8").strip()
THREADS_PERSONA = os.getenv(
    "THREADS_PERSONA",
    "친근하고 진솔한 한국어 톤으로, 과한 이모지나 해시태그 남발 없이 글을 쓴다.",
).strip()
POSTS_PER_RUN = int(os.getenv("POSTS_PER_RUN", "1"))

# 스케줄
SCHEDULE_CRON = os.getenv("SCHEDULE_CRON", "0 9 * * *").strip()
TIMEZONE = os.getenv("TIMEZONE", "Asia/Seoul").strip()

# ===== 안전장치 (밴·노출제한 위험 완화) =====
# 24시간 내 최대 게시 수. 공식 한도(약 250개)보다 낮게 잡아 여유를 둡니다.
DAILY_POST_LIMIT = int(os.getenv("DAILY_POST_LIMIT", "200"))
# 한 번 실행에서 여러 글을 올릴 때 글 사이 최소 대기(초). 봇처럼 보이지 않게.
MIN_POST_INTERVAL_SECONDS = int(os.getenv("MIN_POST_INTERVAL_SECONDS", "60"))
# 스케줄 실행 시각에 더할 랜덤 지터(분). 매일 같은 초에 올리는 패턴을 피합니다.
SCHEDULE_JITTER_MINUTES = int(os.getenv("SCHEDULE_JITTER_MINUTES", "20"))
# 최근 글과 이 비율 이상 유사하면 중복으로 보고 재생성/차단합니다 (0~1).
DUPLICATE_SIMILARITY_THRESHOLD = float(
    os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.8")
)
# 중복 검사 시 비교할 최근 글 개수.
DUPLICATE_LOOKBACK = int(os.getenv("DUPLICATE_LOOKBACK", "30"))

# ===== 이미지 자동 생성 (선택) =====
# 구글 제미나이 이미지 생성 키 (aistudio.google.com에서 무료 발급, 우선 사용)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")).strip()
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image").strip()
# OpenAI 이미지 생성 API 키 (제미나이 없거나 실패 시 폴백)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
# 이미지 생성 모델
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1").strip()
# 이미지 크기
OPENAI_IMAGE_SIZE = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024").strip()
# Imgur 익명 업로드용 Client-ID (생성한 이미지를 공개 URL로 호스팅)
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID", "").strip()
# Pollinations 무료 토큰 (선택 — enter.pollinations.ai 무료 가입, 제한 완화)
POLLINATIONS_TOKEN = os.getenv("POLLINATIONS_TOKEN", "").strip()
# 자동 예약 글당 이미지 장수 (1=빠름/기본, 2=캐러셀)
IMAGES_PER_POST = max(1, min(3, int(os.getenv("IMAGES_PER_POST", "1"))))


def _tunnel_available() -> bool:
    """cloudflared 터널 호스팅이 가능한지(설치 여부)."""
    try:
        from threads_auto import tunnel_host

        return tunnel_host.is_available()
    except Exception:
        return False


def require_image() -> None:
    """이미지 자동 생성에 필요한 값이 있는지 확인합니다.

    생성 키(제미나이 또는 OpenAI) 하나는 필수.
    호스팅은 Imgur 키 또는 cloudflared 터널 중 하나면 됩니다.
    """
    if not GEMINI_API_KEY and not OPENAI_API_KEY:
        raise RuntimeError(
            "이미지 생성 키가 없습니다. .env에 GEMINI_API_KEY(추천, 무료 발급: "
            "aistudio.google.com) 또는 OPENAI_API_KEY를 넣으세요."
        )
    if not IMGUR_CLIENT_ID and not _tunnel_available():
        raise RuntimeError(
            "이미지를 올릴 방법이 없습니다. IMGUR_CLIENT_ID를 넣거나 cloudflared를 설치하세요."
        )


def has_image_support() -> bool:
    """이미지 생성이 가능한지(생성 키 + 호스팅 수단) 여부."""
    return (bool(GEMINI_API_KEY) or bool(OPENAI_API_KEY)) \
        and (bool(IMGUR_CLIENT_ID) or _tunnel_available())


def require_threads() -> None:
    """Threads 게시에 필요한 값이 있는지 확인합니다."""
    _require("THREADS_USER_ID")
    _require("THREADS_ACCESS_TOKEN")


def require_anthropic() -> None:
    """AI 글 생성에 필요한 값이 있는지 확인합니다."""
    _require("ANTHROPIC_API_KEY")
