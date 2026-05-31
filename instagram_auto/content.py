"""카드뉴스 내용 생성 (LLM).

주제를 받아 표지 / 본문 카드들 / 마무리 / 게시 캡션·해시태그를 생성한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import llm
from .config import Config

_SYSTEM = """너는 인스타그램 카드뉴스 전문 에디터다.
주어진 주제로 '저장하고 싶어지는' 정보형 카드뉴스를 기획한다.
- 표지(cover)는 스크롤을 멈추게 하는 강력한 후킹 문구.
- 각 본문 카드는 한 가지 핵심만. 제목은 짧고, 본문은 2~4줄로 쉽게.
- 과장/낚시는 피하고 실제로 유용한 정보를 담는다.
- caption(캡션)에는 '저장/팔로우/공유' 같은 행동유도 문구를 넣지 마라. 그건 시스템이 자동으로 붙인다.
- 대신 comment_question(댓글 유도 질문)을 반드시 만든다. 독자가 자기 경험/의견을 답하고 싶게 만드는 구체적인 질문 한 줄.
반드시 아래 JSON 형식으로만 답하라. 다른 설명 금지.

{
  "cover_title": "표지 핵심 문구 (12자 내외, 줄바꿈은 \\n 가능)",
  "cover_subtitle": "표지 보조 문구 (한 줄)",
  "cards": [
    {"title": "카드 제목 (15자 내외)", "body": "본문 2~4줄. 줄바꿈은 \\n"}
  ],
  "closing_title": "마무리 한마디",
  "closing_cta": "짧은 행동 유도 문구 (예: 저장하고 팔로우)",
  "comment_question": "댓글을 부르는 구체적 질문 한 줄 (예: 여러분은 통장 몇 개로 나눠 쓰세요?)",
  "caption": "게시물 본문 캡션 (2~3문장, 핵심 가치+공감. 행동유도 문구는 넣지 말 것)",
  "hashtags": ["#태그", "... 12~20개"]
}"""

_USER_TEMPLATE = """주제: {topic}
톤앤매너: {tone}
본문 카드 개수: 정확히 {n}장
이 주제로 카드뉴스 1세트를 기획해줘."""


# 모든 게시물 캡션 끝에 자동으로 붙는 참여유도(저장·공유·팔로우) 블록
ENGAGE_FOOTER = (
    "━━━━━━━━━━\n"
    "📌 저장 — 나중에 다시 보기\n"
    "🔖 공유 — 도움될 친구 소환하기\n"
    "✅ 팔로우 — 다음 편도 놓치지 않기"
)


@dataclass
class CardNews:
    cover_title: str
    cover_subtitle: str
    cards: list[dict]
    closing_title: str
    closing_cta: str
    caption: str
    hashtags: list[str] = field(default_factory=list)
    comment_question: str = ""

    @property
    def full_text(self) -> str:
        """캡션 + 댓글유도 질문 + 저장/공유/팔로우 CTA + 해시태그."""
        parts = [self.caption.strip()]
        if self.comment_question:
            parts.append(f"💬 {self.comment_question.strip()}")
        parts.append(ENGAGE_FOOTER)
        body = "\n\n".join(p for p in parts if p)
        tags = " ".join(self.hashtags)
        return f"{body}\n\n{tags}".strip()


def generate_cardnews(
    topic: str, config: Config, tone: str = "친근하고 신뢰감 있는"
) -> CardNews:
    user = _USER_TEMPLATE.format(topic=topic, tone=tone, n=config.card_count)
    data = llm.complete_json(_SYSTEM, user, config)

    cards = []
    for c in data.get("cards", []):
        cards.append(
            {"title": str(c.get("title", "")).strip(), "body": str(c.get("body", "")).strip()}
        )

    hashtags = [_norm(t) for t in data.get("hashtags", []) if str(t).strip()]
    return CardNews(
        cover_title=data.get("cover_title", topic).strip(),
        cover_subtitle=data.get("cover_subtitle", "").strip(),
        cards=cards,
        closing_title=data.get("closing_title", "").strip(),
        closing_cta=data.get("closing_cta", "저장하고 팔로우").strip(),
        caption=data.get("caption", "").strip(),
        hashtags=hashtags,
        comment_question=data.get("comment_question", "").strip(),
    )


def _norm(tag: str) -> str:
    tag = str(tag).strip().replace(" ", "")
    return tag if tag.startswith("#") else f"#{tag}"
