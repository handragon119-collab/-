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
    "반려동물": [
        "안농 나 코니얌!\n인스타 계정 새로 만들어서 스레드도 날라가버려써😂\n코니 아는 칭구들, 새로 보눈 칭구들\n모두모두 칭구해조~!🙌🏻😵‍💫\n스하리=반하리💗 댓글 남겨조",
        "안농 나 9개월 미니비숑 이장군이야 🩷\n병원에서 3.5키로까지 큰다구 했는데 벌써 8.5돌파!!\n나랑 칭구 하지 않울래~? 프로필 링크타구 인스타도 놀러와서\n귀여운 일상 많이 보고가라개 🐶🐶",
        "나 귀요운데 나랑 칭구할뤠?🤍스하리 무조건 반하리간댜",
        "나 어제 스레드 처음 글써봤어.\n팔로우 0명인데 나랑 스친해줄래..?🫶나도 천명 되고 싶은데~\n댕댕이들 나 좀 도와줄랭??\n바로~ 뒷삭없는 반하리하러 갈겡!!\n스하리1000명프로젝트",
        "안녕! 나 밥풀이🍚 유기견보호소에서 왔어!\n나랑 친하게 지낼 친구 있을까?\n나랑 친구해조🫶\n잘부탁할게🐾🤍\n#강아지 #말티즈 #첫스레드",
        "우리 강아지... 귀여운데...\n스하리 하면 반하리 하러 갈게...❤️\n귀여운 강아지 사진 많어...🤣🤣🐶\n우리뚜꾸는 3살이야",
        "나 견생 첫 미용\n휴우~힘드로따\n그래도 나 잘생겨져찌?\n그렇다고 해!!!!!!!!",
        "보호소 출신 이꼬리 😎\n주인 스레드 계정으로 강아지 자랑만 하다 드디어 정식 스레드 계정 만들다 ✨\n입양으로도 사랑스러운 강아지 만날 수 있고 지금도 주인 기다리는 강아지 많다는 거 널리널리 알려야지!!! 🐾🐾",
        "일하는데 챱츄가 계속 쳐다본다…\n귀여워 🐰🤍💦\n#강아지자랑 #강아지최고",
        "ai가 진짜 발달했나바\n사람들이 나보고 다 ai라고해…\n저기요 나 진짜 강아지거든요 다들 너무해 힝🥺",
        "밖에 데리고 나가면 사람들이 인형 같다구 난리🤍🩵",
        "내 월요병 치료제 '동구' 소개할게🤎\n웃고 있는 모습이 너무 귀엽지…\n귀여운 멍뭉이가 세상을 구한다! 힐링 그 자체야🪴",
        "전국에 건강한 노견들이여~~~\n우리 전국 동안 대회 한번하자!\n나이에 비해 젊어보이고 동안 소리 듣는 노견들 한번 붙어보자!\n나는 17세다 드루와 젊고 이쁜 노견들이여",
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
