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
    parser.add_argument("topic", nargs="?", help="게시물 주제 (예: '직장인 점심 스트레칭')")
    parser.add_argument(
        "--mode", choices=["cardnews", "photo"],
        help="콘텐츠 형식 (기본: .env CONTENT_MODE, 미설정 시 cardnews)",
    )
    parser.add_argument("--tone", help="톤앤매너")
    parser.add_argument(
        "--theme", choices=["navy", "mint", "coral", "cream"],
        help="카드뉴스 색상 테마 (기본: .env CARD_THEME)",
    )
    parser.add_argument("--cards", type=int, help="본문 카드 개수 (카드뉴스 모드)")
    parser.add_argument(
        "--dry-run", action="store_true", help="업로드 없이 이미지/내용만 생성"
    )
    parser.add_argument(
        "--topics-file", help="한 줄에 하나씩 주제가 담긴 파일을 일괄 처리"
    )
    args = parser.parse_args(argv)

    if not args.topic and not args.topics_file:
        parser.error("주제를 입력하거나 --topics-file 을 지정하세요.")

    config = Config()
    if args.mode:
        config.content_mode = args.mode
    if args.theme:
        config.card_theme = args.theme
    if args.cards:
        config.card_count = args.cards
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
            print(f"\n----- 생성된 캡션 ({result.mode}) -----")
            print(result.full_text)
            print(f"\n이미지 {len(result.image_paths)}장:")
            for p in result.image_paths:
                print(f"  - {p}")
            print(f"결과: {result.publish_result}")
        except Exception as e:  # noqa: BLE001
            print(f"❌ 실패: {e}", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
