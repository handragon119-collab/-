"""카테고리별 '잘 먹힌 글' 예시를 저장/학습합니다.

- 사용자가 보내준 스레드 스크립트를 시드(SEED)로 내장 → 글쓰기 때 few-shot 예시로 사용
- 웹에서 실제 게시한 글을 카테고리별로 누적 저장 → 점점 그 계정 톤을 학습
저장 위치: data/style_samples.json (gitignore, 이 컴퓨터에만)
"""

from __future__ import annotations

import json
from pathlib import Path

SAMPLES_PATH = Path("data/style_samples.json")

# 사용자가 직접 보내준 한국 반려동물 스레드 실제 예시 (말투·키워드·이모지 학습용)
SEED: dict[str, list[str]] = {
    # 전부 '강아지 본인 1인칭' 톤으로 통일 (주인 시점 금지)
    "반려동물": [
        "안농 나 코니얌!\n인스타 계정 새로 만들어서 스레드도 날라가버려써😂\n나 아는 칭구들, 새로 보눈 칭구들\n모두모두 칭구해조~!🙌🏻😵‍💫\n스하리=반하리💗 댓글 남겨조",
        "안농 나 9개월 미니비숑 이장군이야 🩷\n병원에서 3.5키로까지 큰다구 했는데 나 벌써 8.5돌파!!\n나랑 칭구 하지 않울래~? 프로필 링크타구 인스타도 놀러와서\n나 귀여운 일상 많이 보고가라개 🐶🐶",
        "나 귀요운데 나랑 칭구할뤠?🤍 스하리 무조건 반하리간댜",
        "나 어제 스레드 처음 글써봤어.\n팔로우 0명인데 나랑 스친해줄래..?🫶 나도 천명 되고 싶은데~\n댕댕이들 나 좀 도와줄랭??\n바로~ 뒷삭없는 반하리하러 갈겡!!",
        "안농! 나 밥풀이🍚 유기견보호소에서 왔어!\n나랑 친하게 지낼 칭구 있을까?\n나랑 친구해조🫶\n잘부탁할게🐾🤍\n#강아지 #말티즈 #첫스레드",
        "나 뚜꾸야, 3살🐶\n나 귀엽지...?\n스하리 하면 나두 반하리 갈게...❤️\n귀여운 내 사진 마니 보여줄겡 🤣🤣",
        "나 견생 첫 미용 하구 왔어\n휴우~ 힘드로따\n근데 나 잘생겨져찌?\n그렇다고 해줘!!!!!!!!🐶",
        "나 보호소 출신 이꼬리야 😎\n드디어 내 정식 스레드 계정 생겨써 ✨\n나처럼 입양된 댕댕이도 이렇게 사랑받구 산다구!\n아직 주인 기다리는 칭구들도 많다는 거 알아조 🐾🐾",
        "주인 일하는데 내가 계속 쳐다봤더니…\n나 너무 귀여웠나바 🐰🤍💦\n#강아지자랑 #강아지최고",
        "ai가 진짜 발달했나바\n사람들이 나보고 다 ai래…\n저기요 나 진짜 강아지거든요 다들 너무해 힝🥺",
        "나 밖에 나가면 사람들이 인형 같다구 난리야🤍🩵\n헤헤 나 그렇게 귀여워?",
        "나 동구야🤎 월요일 힘든 칭구들~\n내 웃는 얼굴 보구 힘내라구!\n멍뭉이가 세상 구한다구 ㅎㅎ🪴",
        "나 올해 17살 노견이야!\n근데 나 동안 소리 마니 들어 ㅎㅎ\n전국 건강한 노견들~ 우리 동안 대회 한번 해볼랭?\n드루와 젊구 이쁜 시니어들아 🐶",
    ],
}


def _load() -> dict:
    if SAMPLES_PATH.exists():
        try:
            return json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save(d: dict) -> None:
    SAMPLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    SAMPLES_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def get_samples(category: str | None, limit: int = 10) -> list[str]:
    """카테고리의 예시 글 목록. 최근 학습한 글 우선 + 시드 예시로 채움."""
    if not category:
        return []
    learned = _load().get(category, [])
    out = list(reversed(learned))[:limit]  # 최근 게시한 글 우선
    for s in SEED.get(category, []):
        if len(out) >= limit:
            break
        if s not in out:
            out.append(s)
    return out


def add_sample(category: str | None, text: str) -> None:
    """실제 게시한 글을 그 카테고리의 학습 예시로 저장합니다."""
    if not category or not text:
        return
    text = text.strip()
    if len(text) < 8:
        return
    d = _load()
    arr = d.get(category, [])
    if text in arr:
        return
    arr.append(text)
    d[category] = arr[-300:]  # 너무 커지지 않게
    _save(d)
