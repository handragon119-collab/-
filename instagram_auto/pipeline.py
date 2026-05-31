"""전체 파이프라인: 주제 -> 내용 생성 -> 이미지/카드 렌더 -> 업로드.

두 가지 모드:
  - cardnews : 주제 -> 카드뉴스 내용 -> 여러 장 카드 렌더 -> 캐러셀 업로드
  - photo    : 주제 -> 캡션 -> AI 사진 1장 -> 단일 업로드
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import Config


@dataclass
class PostResult:
    topic: str
    mode: str
    caption: str
    hashtags: list[str]
    full_text: str
    image_paths: list[str]
    publish_result: str
    image_prompt: str = ""
    extra: dict = field(default_factory=dict)


class Pipeline:
    """주제 하나를 받아 인스타그램 게시물을 완성하는 오케스트레이터."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()

    def run(
        self,
        topic: str,
        tone: str | None = None,
        dry_run: bool = False,
        on_log=print,
    ) -> PostResult:
        if self.config.content_mode == "photo":
            return self._run_photo(topic, tone or "친근하고 감성적인", dry_run, on_log)
        return self._run_cardnews(topic, tone or "친근하고 신뢰감 있는", dry_run, on_log)

    # ------------------------------------------------------------------ #
    # 카드뉴스 모드
    # ------------------------------------------------------------------ #
    def _run_cardnews(self, topic, tone, dry_run, on_log) -> PostResult:
        from .card_render import render_cardnews
        from .publisher import publish_carousel

        cfg = self.config
        base = self._base_path(topic)
        agent_report = None

        if cfg.content_engine == "agentic":
            from .agents import generate_cardnews_agentic
            on_log(f"🤖 [1/3] '{topic}' 다중 에이전트 생성 중... (리서치→전략→팩트검증→카피→SEO→리스크)")
            content, report = generate_cardnews_agentic(topic, cfg, tone=tone)
            agent_report = {
                "web_search_used": report.web_search_used,
                "sources": report.sources,
                "risk_flags": report.risk_flags,
                "steps": [s["agent"] for s in report.steps],
            }
            note = "웹검색 ON" if report.web_search_used else "웹검색 미사용(내장지식)"
            on_log(f"   ✓ 에이전트 7단계 완료 · {note} · 근거 {len(report.sources)}개")
        else:
            from .content import generate_cardnews
            on_log(f"📝 [1/3] '{topic}' 카드뉴스 내용 생성 중... (모델={cfg.caption_provider})")
            content = generate_cardnews(topic, cfg, tone=tone)
        on_log(f"   ✓ 표지 + 본문 {len(content.cards)}장 + 마무리 기획 완료")

        on_log(f"🎨 [2/3] 카드 {len(content.cards) + 2}장 렌더링 중... (테마={cfg.card_theme})")
        paths = render_cardnews(content, cfg, str(base))
        on_log(f"   ✓ 카드 {len(paths)}장 저장: {Path(paths[0]).parent}/")

        pub = self._do_publish(
            lambda: publish_carousel(paths, content.full_text, cfg), dry_run, on_log,
            slides=len(paths),
        )

        result = PostResult(
            topic=topic, mode="cardnews", caption=content.caption,
            hashtags=content.hashtags, full_text=content.full_text,
            image_paths=paths, publish_result=pub,
            extra={"cover_title": content.cover_title, "cards": content.cards,
                   "agent_report": agent_report},
        )
        self._save_meta(base, result)
        return result

    # ------------------------------------------------------------------ #
    # 단일 사진 모드
    # ------------------------------------------------------------------ #
    def _run_photo(self, topic, tone, dry_run, on_log) -> PostResult:
        from .caption import generate_caption
        from .image_gen import generate_image
        from .publisher import publish

        cfg = self.config
        base = self._base_path(topic)

        on_log(f"📝 [1/3] '{topic}' 캡션 생성 중...")
        cap = generate_caption(topic, cfg, tone=tone)
        on_log(f"   ✓ 캡션 완성 (해시태그 {len(cap.hashtags)}개)")

        on_log(f"🎨 [2/3] 이미지 생성 중... (provider={cfg.image_provider})")
        image_path = generate_image(cap.image_prompt, cfg, f"{base}.jpg")
        on_log(f"   ✓ 이미지 저장: {image_path}")

        pub = self._do_publish(
            lambda: publish(image_path, cap.full_text, cfg), dry_run, on_log, slides=1
        )

        result = PostResult(
            topic=topic, mode="photo", caption=cap.caption, hashtags=cap.hashtags,
            full_text=cap.full_text, image_paths=[image_path], publish_result=pub,
            image_prompt=cap.image_prompt,
        )
        self._save_meta(base, result)
        return result

    # ------------------------------------------------------------------ #
    # 공통 헬퍼
    # ------------------------------------------------------------------ #
    def _base_path(self, topic: str) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        base = Path(self.config.output_dir) / f"{stamp}_{_slugify(topic)}"
        base.parent.mkdir(parents=True, exist_ok=True)
        return base

    def _do_publish(self, action, dry_run, on_log, slides) -> str:
        cfg = self.config
        if dry_run or cfg.publisher == "none":
            msg = "업로드 건너뜀 (dry-run)" if dry_run else "업로드 건너뜀 (PUBLISHER=none)"
            on_log(f"🚀 [3/3] {msg}")
            return msg
        on_log(f"🚀 [3/3] 인스타그램 업로드 중... (publisher={cfg.publisher}, {slides}장)")
        result = action()
        on_log(f"   ✓ {result}")
        return result

    def _save_meta(self, base: Path, result: PostResult) -> None:
        with open(f"{base}.json", "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w가-힣]+", "-", text.strip())
    return text.strip("-")[:40] or "post"
