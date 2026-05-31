"""Claude API로 스레드 게시글을 자동 생성합니다."""

from __future__ import annotations

import random
from pathlib import Path

import anthropic

# Threads 본문은 최대 500자입니다. 여유를 두고 생성하도록 지시합니다.
MAX_THREADS_CHARS = 500

SYSTEM_PROMPT = """너는 SNS 'Threads(스레드)'에 올릴 짧은 글을 쓰는 한국어 작가다.

작성 규칙:
- 한 편의 완결된 게시글을 한국어로 작성한다.
- 길이는 공백 포함 450자 이내로, 스레드 한 게시물에 들어가도록 한다.
- 사람이 직접 쓴 것처럼 자연스럽고 진솔하게 쓴다.
- 해시태그는 정말 필요할 때 1~2개만, 이모지는 과하지 않게 쓴다.
- "오늘은 ~에 대해 이야기해볼게요" 같은 진부한 서두 없이 바로 본론으로 들어간다.
- 마크다운 문법(##, **, - 등)을 쓰지 않는다. 순수 텍스트로만 쓴다.
- 설명이나 따옴표 없이, 게시글 본문만 출력한다."""


def load_topics(path: str = "topics.txt") -> list[str]:
    """topics.txt에서 주제 목록을 읽습니다."""
    p = Path(path)
    if not p.exists():
        return []
    topics = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            topics.append(line)
    return topics


class ContentGenerator:
    def __init__(self, api_key: str, model: str, persona: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.persona = persona

    def generate(self, topic: str | None = None) -> str:
        """주제를 받아 게시글 본문을 생성합니다. topic이 없으면 자유 주제로 작성."""
        if topic:
            user_msg = f"다음 주제로 스레드 게시글을 한 편 써줘:\n\n{topic}"
        else:
            user_msg = "오늘 올릴 만한 스레드 게시글을 자유 주제로 한 편 써줘."

        # 페르소나는 매 요청 동일하므로 캐시 대상에 포함시킨다.
        system = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT + f"\n\n추가 톤 가이드: {self.persona}",
                "cache_control": {"type": "ephemeral"},
            }
        ]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        # 혹시 500자를 넘으면 안전하게 잘라낸다.
        if len(text) > MAX_THREADS_CHARS:
            text = text[:MAX_THREADS_CHARS].rstrip()
        return text

    def generate_from_random_topic(self, topics_path: str = "topics.txt") -> tuple[str, str | None]:
        """주제 목록에서 무작위로 골라 글을 생성합니다. (본문, 사용한 주제) 반환."""
        topics = load_topics(topics_path)
        topic = random.choice(topics) if topics else None
        return self.generate(topic), topic

    def generate_image_prompt(self, post_text: str) -> str:
        """게시글 내용에 어울리는 이미지 생성용 프롬프트(영어)를 만듭니다."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "다음 SNS 게시글에 어울리는 사진/일러스트 한 장을 만들기 위한 "
                        "이미지 생성 프롬프트를 영어로 한 문단 써줘. 사람 얼굴이나 글자가 "
                        "들어가지 않는, 분위기 위주의 깔끔한 이미지로. 설명 없이 프롬프트만 출력:\n\n"
                        + post_text
                    ),
                }
            ],
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
