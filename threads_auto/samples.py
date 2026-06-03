"""계정별 '잘 먹힌 글' 예시를 저장/학습합니다.

- 학습은 '계정(아이디)별'로 저장됩니다 → 계정마다 자기 톤이 따로 쌓임.
- 페르소나(pet/studio 등)별 시드(SEED)를 기본 예시로 제공.
저장 위치: data/style_samples.json (gitignore, 이 컴퓨터에만)
구조: { "<account_id>": ["글", ...] }
"""

from __future__ import annotations

import json
from pathlib import Path

SAMPLES_PATH = Path("data/style_samples.json")

# 페르소나별 시드 예시 (계정에 학습 글이 쌓이기 전 기본 톤 제공)
SEED: dict[str, list[str]] = {
    "pet": [
        "안농 나 코니얌!\n인스타 계정 새로 만들어서 스레드도 날라가버려써😂\n나 아는 칭구들, 새로 보눈 칭구들\n모두모두 칭구해조~!🙌🏻😵‍💫\n스하리=반하리💗 댓글 남겨조",
        "안농 나 9개월 미니비숑 이장군이야 🩷\n병원에서 3.5키로까지 큰다구 했는데 나 벌써 8.5돌파!!\n나랑 칭구 하지 않울래~? 프로필 링크타구 인스타도 놀러와서\n나 귀여운 일상 많이 보고가라개 🐶🐶",
        "나 귀요운데 나랑 칭구할뤠?🤍 스하리 무조건 반하리간댜",
        "나 어제 스레드 처음 글써봤어.\n팔로우 0명인데 나랑 스친해줄래..?🫶 나도 천명 되고 싶은데~\n댕댕이들 나 좀 도와줄랭??\n바로~ 뒷삭없는 반하리하러 갈겡!!",
        "안농! 나 밥풀이🍚 유기견보호소에서 왔어!\n나랑 친하게 지낼 칭구 있을까?\n나랑 친구해조🫶\n잘부탁할게🐾🤍\n#강아지 #말티즈 #첫스레드",
        "나 뚜꾸야, 3살🐶\n나 귀엽지...?\n스하리 하면 나두 반하리 갈게...❤️\n귀여운 내 사진 마니 보여줄겡 🤣🤣",
        "나 견생 첫 미용 하구 왔어\n휴우~ 힘드로따\n근데 나 잘생겨져찌?\n그렇다고 해줘!!!!!!!!🐶",
        "나 동구야🤎 월요일 힘든 칭구들~\n내 웃는 얼굴 보구 힘내라구!\n멍뭉이가 세상 구한다구 ㅎㅎ🪴",
    ],
    "studio": [
        "사진은 찍을 수 있을 때 찍어야 해. 진짜로.\n오늘도 '진작 올 걸' 하는 손님 봤거든.\n미루지 마. 시간은 안 기다려줘.\n너넨 가족사진 마지막으로 언제 찍었어?",
        "오늘 할머니가 영정사진 찍으러 오셨어.\n근데 활짝 웃으시더라.\n\"잘 나와야 자식들 덜 운다\"고.\n사진 찍다 내가 더 뭉클했네 🤍",
        "10년 만에 가족사진 찍으러 온 가족이 있었어.\n다들 늙었더라. 애기였던 애가 대학생이고.\n근데 그게 또 좋더라.\n시간이 다 담겨 있어서.",
        "증명사진 찍을 때 다들 표정이 굳어 ㅋㅋ\n'편하게 웃으세요' 가 제일 어렵지?\n괜찮아. 원래 다 그래.\n내가 웃겨줄 테니까 그냥 와.",
        "사진관 오래 하다 보면 알게 돼.\n잘 나온 사진보다, 그날의 표정이 남는다는 거.\n완벽하지 않아도 괜찮아.\n그 순간이 진짜니까 📷",
        "프로필 사진 미루다가\n결국 셀카로 이력서 낸 사람~\n나도 알아 귀찮은 거.\n근데 한 장은 제대로 있어야 해. 너 생각보다 잘 나와.",
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


def get_samples(account_id: str | None, persona: str = "general", limit: int = 10) -> list[str]:
    """계정의 학습 예시(최근 우선) + 페르소나 시드로 채워 반환."""
    learned = _load().get(account_id or "", [])
    out = list(reversed(learned))[:limit]
    for s in SEED.get(persona or "", []):
        if len(out) >= limit:
            break
        if s not in out:
            out.append(s)
    return out


def add_sample(account_id: str | None, text: str) -> None:
    """실제 게시한 글을 그 계정의 학습 예시로 저장합니다."""
    if not account_id or not text:
        return
    text = text.strip()
    if len(text) < 8:
        return
    d = _load()
    arr = d.get(account_id, [])
    if text in arr:
        return
    arr.append(text)
    d[account_id] = arr[-300:]
    _save(d)

