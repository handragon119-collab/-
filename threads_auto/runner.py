"""글 생성 → 게시 → 기록까지 한 번의 실행 흐름을 담당합니다."""

import json
from datetime import datetime
from pathlib import Path

import config
from threads_auto.content_generator import ContentGenerator
from threads_auto.threads_client import ThreadsClient

LOG_PATH = Path("data/posted_log.jsonl")


def _log_post(record: dict) -> None:
    """게시 결과를 data/posted_log.jsonl 에 한 줄씩 누적 기록합니다."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_once(text: str | None = None, dry_run: bool = False) -> None:
    """한 번 실행: 글을 만들고(또는 받은 글로) 스레드에 게시합니다.

    text가 주어지면 그 글을 그대로 게시하고, 없으면 AI가 생성합니다.
    dry_run=True면 실제 게시 없이 생성 결과만 출력합니다.
    """
    config.require_anthropic()

    generator = ContentGenerator(
        api_key=config.ANTHROPIC_API_KEY,
        model=config.CLAUDE_MODEL,
        persona=config.THREADS_PERSONA,
    )

    posts = config.POSTS_PER_RUN if text is None else 1

    client = None
    if not dry_run:
        config.require_threads()
        client = ThreadsClient(config.THREADS_USER_ID, config.THREADS_ACCESS_TOKEN)

    for i in range(posts):
        if text is not None:
            body, topic = text, None
        else:
            body, topic = generator.generate_from_random_topic()

        print("\n" + "=" * 50)
        print(f"[{i + 1}/{posts}] 생성된 글" + (f" (주제: {topic})" if topic else ""))
        print("-" * 50)
        print(body)
        print("=" * 50)

        if dry_run:
            print("dry-run 모드: 실제 게시는 하지 않았습니다.")
            continue

        post_id = client.post_text(body)
        print(f"✅ 게시 완료! post_id={post_id}")
        _log_post(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "topic": topic,
                "text": body,
                "post_id": post_id,
            }
        )
