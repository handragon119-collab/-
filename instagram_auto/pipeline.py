"""전체 파이프라인: 주제 -> 캡션 -> 이미지 -> 업로드."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .caption import CaptionResult, generate_caption
from .config import Config
from .image_gen import generate_image
from .publisher import publish


@dataclass
class PostResult:
    topic: str
    caption: str
    hashtags: list[str]
    image_prompt: str
    image_path: str
    full_text: str
    publish_result: str


class Pipeline:
    """주제 하나를 받아 인스타그램 게시물을 완성하는 오케스트레이터."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()

    def run(
        self,
        topic: str,
        tone: str = "친근하고 감성적인",
        dry_run: bool = False,
        on_log=print,
    ) -> PostResult:
        cfg = self.config
        slug = _slugify(topic)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        base = Path(cfg.output_dir) / f"{stamp}_{slug}"
        base.parent.mkdir(parents=True, exist_ok=True)

        on_log(f"📝 [1/3] '{topic}' 캡션 생성 중...")
        cap: CaptionResult = generate_caption(topic, cfg, tone=tone)
        on_log(f"   ✓ 캡션 완성 (해시태그 {len(cap.hashtags)}개)")

        on_log(f"🎨 [2/3] 이미지 생성 중... (provider={cfg.image_provider})")
        image_path = generate_image(cap.image_prompt, cfg, f"{base}.jpg")
        on_log(f"   ✓ 이미지 저장: {image_path}")

        if dry_run or cfg.publisher == "none":
            pub = "업로드 건너뜀 (dry-run)" if dry_run else "업로드 건너뜀 (PUBLISHER=none)"
            on_log(f"🚀 [3/3] {pub}")
        else:
            on_log(f"🚀 [3/3] 인스타그램 업로드 중... (publisher={cfg.publisher})")
            pub = publish(image_path, cap.full_text, cfg)
            on_log(f"   ✓ {pub}")

        result = PostResult(
            topic=topic,
            caption=cap.caption,
            hashtags=cap.hashtags,
            image_prompt=cap.image_prompt,
            image_path=image_path,
            full_text=cap.full_text,
            publish_result=pub,
        )
        # 결과 메타데이터 저장
        with open(f"{base}.json", "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
        return result


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w가-힣]+", "-", text.strip())
    return text.strip("-")[:40] or "post"
