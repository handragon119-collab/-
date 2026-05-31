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


def require_threads() -> None:
    """Threads 게시에 필요한 값이 있는지 확인합니다."""
    _require("THREADS_USER_ID")
    _require("THREADS_ACCESS_TOKEN")


def require_anthropic() -> None:
    """AI 글 생성에 필요한 값이 있는지 확인합니다."""
    _require("ANTHROPIC_API_KEY")
