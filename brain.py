"""
brain.py - 자비스의 두뇌(LLM).

Claude API에 대화를 보내 자연스러운 답을 받는다.
API 키가 없으면 간단한 규칙 기반 답으로 대신한다(완전 오프라인 데모).
대화 맥락을 기억하기 위해 최근 메시지를 들고 다닌다.
"""
from __future__ import annotations

import os

SYSTEM_PROMPT = (
    "당신은 아이언맨의 인공지능 비서 '자비스(JARVIS)'입니다. "
    "차분하고 정중하며 약간의 위트가 있는 집사 같은 말투로 한국어로 대답합니다. "
    "사용자를 '님' 또는 상황에 따라 정중하게 부릅니다. "
    "답변은 음성으로 읽히므로 1~3문장으로 짧고 명확하게 합니다. "
    "목록이나 코드, 마크다운 기호는 쓰지 않고 말하듯이 답합니다."
)


class Brain:
    def __init__(self, model: str | None = None, max_history: int = 12):
        self.model = model or os.getenv("JARVIS_MODEL", "claude-sonnet-4-6")
        self.max_history = max_history
        self.history: list[dict] = []
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("[brain] ANTHROPIC_API_KEY가 없어 규칙 기반(오프라인) 모드로 동작합니다.")
            return
        try:
            import anthropic  # type: ignore

            self._client = anthropic.Anthropic(api_key=api_key)
        except Exception as exc:
            print(f"[brain] anthropic 초기화 실패, 오프라인 모드로 전환합니다. ({exc})")
            self._client = None

    @property
    def online(self) -> bool:
        return self._client is not None

    def think(self, user_text: str) -> str:
        """사용자 발화에 대한 자비스의 답을 만든다."""
        self.history.append({"role": "user", "content": user_text})
        self.history = self.history[-self.max_history:]

        if not self._client:
            reply = self._offline_reply(user_text)
        else:
            try:
                resp = self._client.messages.create(
                    model=self.model,
                    max_tokens=300,
                    system=SYSTEM_PROMPT,
                    messages=self.history,
                )
                reply = "".join(
                    block.text for block in resp.content if block.type == "text"
                ).strip()
            except Exception as exc:
                print(f"[brain] API 호출 실패: {exc}")
                reply = "죄송합니다, 지금은 생각을 정리하기 어렵네요. 잠시 후 다시 시도해 주세요."

        self.history.append({"role": "assistant", "content": reply})
        return reply

    def _offline_reply(self, text: str) -> str:
        """API 키 없이도 최소한의 대화가 되도록 하는 간단 응답."""
        t = text.lower()
        if any(k in t for k in ["고마워", "감사", "thank"]):
            return "천만에요. 언제든 도와드리겠습니다."
        if any(k in t for k in ["잘 자", "굿나잇", "good night"]):
            return "편히 쉬세요. 필요하면 다시 불러주십시오."
        return (
            "지금은 두뇌(Claude API)에 연결되지 않아 자세한 답은 어렵습니다. "
            ".env 파일에 ANTHROPIC_API_KEY를 넣으시면 제대로 대화할 수 있습니다."
        )
