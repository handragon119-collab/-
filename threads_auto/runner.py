"""글 생성 → 게시 → 기록까지 한 번의 실행 흐름을 담당합니다."""

from __future__ import annotations

import json
import time
from datetime import datetime

import random

import config
from threads_auto import safety
from threads_auto.content_generator import ContentGenerator, load_topics
from threads_auto.threads_client import ThreadsClient
from threads_auto.image_generator import ImageError, create_image_url_auto
from threads_auto.pipeline import ThreadsPipeline

LOG_PATH = safety.LOG_PATH


def _log_post(record: dict) -> None:
    """게시 결과를 data/posted_log.jsonl 에 한 줄씩 누적 기록합니다."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _make_post(pipe: ThreadsPipeline, generator: ContentGenerator,
               topic: str) -> str:
    """고급 파이프라인으로 글을 생성하되, 실패하면 기본 생성으로 폴백합니다."""
    try:
        return pipe.run(topic)["text"]
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠️ 고급 생성 실패 → 기본 생성으로 진행 ({exc})")
        return generator.generate(topic)


def _generate_unique(pipe: ThreadsPipeline, generator: ContentGenerator,
                     max_tries: int = 3) -> tuple[str, str | None]:
    """중복(유사) 글을 피해 최대 max_tries번 재생성합니다."""
    topics = load_topics() or [None]
    topic = random.choice(topics)
    body = _make_post(pipe, generator, topic) if topic else generator.generate(None)
    for attempt in range(max_tries):
        dup, sim = safety.is_duplicate(
            body,
            config.DUPLICATE_SIMILARITY_THRESHOLD,
            config.DUPLICATE_LOOKBACK,
        )
        if not dup:
            return body, topic
        print(f"  ↻ 최근 글과 유사({sim:.0%}) → 재생성 ({attempt + 1}/{max_tries})")
        topic = random.choice(topics)
        body = _make_post(pipe, generator, topic) if topic else generator.generate(None)
    print("  ⚠️ 유사 글이 계속 생성됨. 마지막 결과로 진행합니다.")
    return body, topic


def run_once(text: str | None = None, dry_run: bool = False,
             with_image: bool = False) -> None:
    """한 번 실행: 글을 만들고(또는 받은 글로) 스레드에 게시합니다.

    text가 주어지면 그 글을 그대로 게시하고, 없으면 AI가 생성합니다.
    dry_run=True면 실제 게시 없이 생성 결과만 출력합니다.
    with_image=True면 글에 어울리는 이미지를 AI로 생성해 함께 게시합니다.
    """
    config.require_anthropic()
    if with_image and not dry_run:
        config.require_image()

    generator = ContentGenerator(
        api_key=config.ANTHROPIC_API_KEY,
        model=config.CLAUDE_MODEL,
        persona=config.THREADS_PERSONA,
    )
    pipe = ThreadsPipeline(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL)

    posts = config.POSTS_PER_RUN if text is None else 1

    client = None
    if not dry_run:
        config.require_threads()
        client = ThreadsClient(config.THREADS_USER_ID, config.THREADS_ACCESS_TOKEN)

    for i in range(posts):
        # ── 안전장치 ①: 일일 게시 한도 가드 (실제 게시 시에만) ──
        if not dry_run:
            ok, posted = safety.check_daily_limit(config.DAILY_POST_LIMIT)
            if not ok:
                print(
                    f"🛑 최근 24시간 게시 수 {posted}개가 한도({config.DAILY_POST_LIMIT})에 "
                    "도달해 중단합니다. (API rate limit·스팸 탐지 보호)"
                )
                return

        # ── 글 준비: 직접 입력 글 또는 AI 생성(중복 회피) ──
        if text is not None:
            body, topic = text, None
        else:
            body, topic = _generate_unique(pipe, generator)

        print("\n" + "=" * 50)
        print(f"[{i + 1}/{posts}] 생성된 글" + (f" (주제: {topic})" if topic else ""))
        print(f"길이: {len(body)}자")
        print("-" * 50)
        print(body)
        print("=" * 50)

        if dry_run:
            print("dry-run 모드: 실제 게시는 하지 않았습니다.")
            continue

        # ── 이미지 생성(선택) ──
        image_url = None
        if with_image:
            try:
                print("  🎨 이미지 생성 중…")
                prompt = pipe.image_prompt(body)
                image_url = create_image_url_auto(
                    config.OPENAI_API_KEY,
                    config.IMGUR_CLIENT_ID,
                    prompt,
                    model=config.OPENAI_IMAGE_MODEL,
                    size=config.OPENAI_IMAGE_SIZE,
                )
                print(f"  🖼️ 이미지 준비 완료: {image_url}")
            except ImageError as exc:
                print(f"  ⚠️ 이미지 생성 실패 → 글만 게시합니다. ({exc})")
                image_url = None

        if image_url:
            post_id = client.post_image(body, image_url)
        else:
            post_id = client.post_text(body)
        print(f"✅ 게시 완료! post_id={post_id}")
        _log_post(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "topic": topic,
                "text": body,
                "post_id": post_id,
                "image_url": image_url,
            }
        )

        # ── 안전장치 ②: 글 사이 최소 간격 (봇 패턴 회피) ──
        if i < posts - 1 and config.MIN_POST_INTERVAL_SECONDS > 0:
            print(f"  ⏳ 다음 글까지 {config.MIN_POST_INTERVAL_SECONDS}초 대기")
            time.sleep(config.MIN_POST_INTERVAL_SECONDS)
