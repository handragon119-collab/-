"""스레드 자동 업로드 프로그램 진입점(CLI).

사용 예:
  python main.py post                 # AI가 글 생성 후 1회 게시
  python main.py post --dry-run       # 게시 없이 생성 결과만 미리보기
  python main.py post --text "직접 쓴 글"   # 입력한 글을 그대로 게시
  python main.py post --with-image    # 글 + AI 생성 이미지 함께 게시
  python main.py schedule             # 스케줄에 따라 자동 반복 게시
"""

import argparse
import sys

from threads_auto.runner import run_once
from threads_auto import scheduler
from threads_auto.threads_client import ThreadsError


def main() -> None:
    parser = argparse.ArgumentParser(description="스레드(Threads) 자동 업로드 프로그램")
    sub = parser.add_subparsers(dest="command", required=True)

    p_post = sub.add_parser("post", help="한 번 실행: 글 생성 후 게시")
    p_post.add_argument("--text", default=None, help="이 텍스트를 그대로 게시 (생략 시 AI 생성)")
    p_post.add_argument("--dry-run", action="store_true", help="실제 게시 없이 생성 결과만 출력")
    p_post.add_argument("--with-image", action="store_true", help="AI로 이미지를 생성해 함께 게시")

    sub.add_parser("schedule", help="스케줄에 따라 자동 반복 게시")

    args = parser.parse_args()

    try:
        if args.command == "post":
            run_once(text=args.text, dry_run=args.dry_run, with_image=args.with_image)
        elif args.command == "schedule":
            scheduler.start()
    except (RuntimeError, ThreadsError) as exc:
        print(f"\n⚠️  오류: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
