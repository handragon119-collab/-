"""커맨드라인 인터페이스.

사용 예:
  python -m instagram_auto "가을 캠핑 감성"
  python -m instagram_auto "홈카페 라떼아트" --tone "전문적이고 깔끔한" --dry-run
  python -m instagram_auto --topics-file topics.txt   # 여러 주제 일괄 처리
"""

from __future__ import annotations

import argparse
import sys

from .config import Config
from .pipeline import Pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="instagram_auto",
        description="주제를 입력하면 AI가 이미지+캡션을 만들어 인스타그램에 자동 업로드합니다.",
    )
    parser.add_argument("topic", nargs="?", help="게시물 주제 (예: '가을 캠핑 감성')")
    parser.add_argument(
        "--tone", default="친근하고 감성적인", help="캡션 톤앤매너 (기본: 친근하고 감성적인)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="업로드 없이 이미지/캡션만 생성"
    )
    parser.add_argument(
        "--topics-file", help="한 줄에 하나씩 주제가 담긴 파일을 일괄 처리"
    )
    args = parser.parse_args(argv)

    if not args.topic and not args.topics_file:
        parser.error("주제를 입력하거나 --topics-file 을 지정하세요.")

    config = Config()
    pipeline = Pipeline(config)

    topics: list[str] = []
    if args.topics_file:
        with open(args.topics_file, encoding="utf-8") as f:
            topics = [line.strip() for line in f if line.strip()]
    if args.topic:
        topics.insert(0, args.topic)

    exit_code = 0
    for i, topic in enumerate(topics, 1):
        print(f"\n{'='*60}\n[{i}/{len(topics)}] 주제: {topic}\n{'='*60}")
        try:
            result = pipeline.run(topic, tone=args.tone, dry_run=args.dry_run)
            print("\n----- 생성된 캡션 -----")
            print(result.full_text)
            print(f"\n이미지: {result.image_path}")
            print(f"결과: {result.publish_result}")
        except Exception as e:  # noqa: BLE001
            print(f"❌ 실패: {e}", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
