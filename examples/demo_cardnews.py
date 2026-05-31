"""카드뉴스 데모/테스트 스크립트.

실제 Pipeline 코드를 그대로 사용하되, LLM 호출(generate_cardnews)만
미리 작성한 현실적인 내용으로 대체해 전체 흐름(내용→카드 렌더→메타 저장)을 검증한다.
업로드는 PUBLISHER=none 으로 건너뛴다.

실행:  python examples/demo_cardnews.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from instagram_auto import Config, Pipeline
from instagram_auto import content as content_mod
from instagram_auto.content import CardNews

# --- LLM이 생성했다고 가정한 카드뉴스 내용 (사회초년생 돈 관리) ---
DEMO = CardNews(
    cover_title="사회초년생\n돈 관리 5원칙",
    cover_subtitle="첫 월급부터 시작하는 진짜 재테크",
    cards=[
        {"title": "1. 통장을 4개로 쪼개라",
         "body": "월급·생활비·비상금·투자 통장을 분리하세요.\n돈의 흐름이 보이면 새는 돈이 줄어듭니다."},
        {"title": "2. 비상금 3개월치 먼저",
         "body": "투자보다 먼저 '생활비 3개월치'를 모으세요.\n갑작스러운 일에도 빚지지 않는 안전망이에요."},
        {"title": "3. 고정비부터 점검",
         "body": "안 쓰는 구독, 비싼 통신비가 매달 빠져나가요.\n고정비 1만원 절약 = 평생 자산입니다."},
        {"title": "4. 선저축 후지출",
         "body": "쓰고 남은 걸 모으면 절대 안 모입니다.\n월급날 자동이체로 먼저 떼어 두세요."},
        {"title": "5. 소액이라도 투자 시작",
         "body": "월 10만원이라도 일찍 시작하는 게 핵심.\n시간이 복리를 만들어 줍니다."},
    ],
    closing_title="작은 습관이\n자산을 만듭니다",
    closing_cta="저장하고 팔로우",
    caption="첫 월급 받으면 가장 먼저 해야 할 5가지, 정리해봤어요 💰\n오늘부터 하나씩만 실천해보세요!",
    hashtags=["#사회초년생", "#재테크", "#돈관리", "#first월급", "#저축",
              "#짠테크", "#money", "#직장인", "#투자입문", "#경제공부"],
)


def main():
    # 실제 LLM 호출을 데모 내용으로 대체
    content_mod.generate_cardnews = lambda topic, cfg, tone=None: DEMO

    cfg = Config()
    cfg.content_mode = "cardnews"
    cfg.card_theme = "cream"        # 고급/감성 테마
    cfg.brand_handle = "@money.note"
    cfg.publisher = "none"          # 업로드는 건너뜀
    cfg.output_dir = "output"

    result = Pipeline(cfg).run("사회초년생 돈 관리 원칙")

    print("\n" + "=" * 50)
    print("✅ 테스트 완료")
    print("=" * 50)
    print(f"모드: {result.mode}")
    print(f"슬라이드: {len(result.image_paths)}장")
    print("\n[게시될 캡션]")
    print(result.full_text)


if __name__ == "__main__":
    main()
