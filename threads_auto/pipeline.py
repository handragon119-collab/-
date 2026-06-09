"""고급 콘텐츠 생성 파이프라인 (다단계 에이전트).

흐름:
  1) 리서치+전략+리스크 에이전트 — 웹 검색으로 주제를 조사하고, 차별화 각도/구조/
     민감도/팩트 필요 여부를 판단
  2) 팩트 검증 에이전트 (필요할 때만) — 웹 검색으로 확인하되, 정부·공공기관·학술·
     주요 언론 등 '공신력 있는 출처'로 검증된 사실만 인정
  3) 글쓰기 에이전트 — 한국 스레드 특유의 '반말·훅 중심·짧은 호흡' 바이럴 문체로 작성
  4) SEO·편집은 글쓰기 단계에 통합 (키워드/해시태그 절제)

웹 검색은 Anthropic API에 내장된 server-side web_search 도구를 사용합니다.
(추가 키 불필요 — Claude API 키만 있으면 됨)

주의: Threads의 '조회수 상위 글'을 직접 스크래핑할 공개 API는 없습니다.
따라서 본 파이프라인은 웹 검색 + 한국 스레드 고성과 글의 문체 특성을 학습한
가이드로 그에 최대한 근접한 글을 만듭니다.
"""

from __future__ import annotations

import json
import re

import anthropic

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}

# 공신력 있는 출처로 인정하는 도메인 힌트(팩트 검증 에이전트에 안내)
CREDIBLE_SOURCE_HINT = (
    "정부(.go.kr, .gov), 공공기관, 학술(.ac.kr, .edu, 학회/저널), 통계청·"
    "한국은행 등 공식 통계, 주요 언론사(연합뉴스·KBS 등), 국제기구(WHO·OECD 등)"
)

# 한국 스레드 고성과 글의 문체 가이드 (반말 · MZ 트렌드 · 짧게)
STYLE_GUIDE = """너는 한국 'Threads(스레드)'에서 조회수가 잘 터지는 글을 쓰는 사람이다.
지금 한국 스레드에서 잘 먹히는 MZ 감성 그대로 쓴다.

[필수 규칙]
- 반말. 친구한테 톡 보내듯, 혼잣말하듯 툭 던진다.
- 짧게. 진짜 짧게. 공백 포함 80~200자. 길면 무조건 잘라낸다.
- 첫 줄에서 승부 본다. 스크롤 멈추게 하는 한 방으로 시작.
  (공감 저격 / 의외의 고백 / 반전 / 솔직한 짜증·설렘 중 하나)
- 한 문장 한 줄. 줄바꿈을 적극적으로. 호흡이 툭툭 끊겨야 한다.
- 멋부린 마무리, 교훈, 에세이 톤 금지. 그냥 사람처럼.
- 구체적인 디테일 하나는 꼭. (장면·숫자·찰나의 감정)
- 광고 같으면 망한다. 정보가 있어도 경험에 슬쩍 녹인다.
- 해시태그 0~1개, 이모지 0~1개. 남발 금지.
- 오글거리는 유행어 억지로 넣지 마라. 자연스러운 게 MZ다.
- 마지막 줄은 가볍게. 여운 한 줄 또는 진짜 궁금한 듯한 질문.
- 마크다운(##, **, - ) 쓰지 않는다. 순수 텍스트.
- 설명·따옴표 없이 게시글 본문만 출력한다."""

# 프리미엄 디자인 이미지 프롬프트 가이드 (애플·나이키·무인양품 감성)
DESIGN_GUIDE = (
    "Minimal, premium editorial aesthetic inspired by Apple, Nike, and Muji: "
    "lots of negative space, restrained neutral palette with a single accent color, "
    "soft natural light, refined textures, calm high-end mood, object or scene centered, "
    "magazine-quality composition. No text, no logos, no human faces. Subtle soft shadows."
)


# 카테고리별 전용 문체 (선택한 카테고리에 맞춰 글쓰기 에이전트에 덧붙임)
PET_STYLE = """
[반려동물 카테고리 전용 — 한국 스레드 '댕댕이/냥이' 커뮤니티 말투로 써라]
‼️ 가장 중요: 이 글은 사람이 아니라 '반려동물 본인'이 말하는 글이다.
   '나'는 무조건 강아지(또는 고양이)다. 절대 주인(집사) 시점으로 쓰지 마라.
   "우리 강아지~", "내 강아지가~" 같은 주인 시점 표현 금지. 강아지가 직접 "나 ~야!" 라고 말해라.
‼️ 강아지는 '자기 자신에 대해서만' 이야기한다. 자기 하루·기분·모습·있었던 일.
   상대를 부르는 호칭(너, 너네, 그쪽, 당신, 너희, 칭구들아 등)을 절대 쓰지 마라.
   "나랑 친구해줘", "맞팔해", "댓글 남겨줘", "너넨 어때?" 처럼 남에게 거는 요청·질문도 금지.
   (강아지가 처음 보는 사람한테 너·당신 하는 건 버릇없어 보인다.)
   마무리도 남에게 묻지 말고, 혼잣말이나 자기 감정으로 닫아라.

‼️‼️ [가장 자주 망치는 부분 — 매번 완전히 다르게 써라]
   글마다 첫 줄·문장 구조·이모지·맞춤법 비틀기·마무리가 '전부 새로워야' 한다.
   같은 시작, 같은 표현, 같은 마무리를 두 번 쓰면 실패다.
   ❌ 매번 "안농 나 ~야" 로 시작하지 마라. (이거 한 번 쓰면 다음엔 절대 금지)
   ❌ "혀 메롱", "폼나찌", "고개 갸웃", "두근두근", "몽글몽글", "~보이지롱" 같은
      특정 표현을 매번 반복하지 마라. 한 번 썼으면 다른 글에선 다른 단어를 찾아라.
   ❌ 아래 예시나 내가 전에 쓴 글의 문장·시작·이모지 조합을 복붙·재탕하지 마라.
   ✅ 시작을 매번 바꿔라. 예시 메뉴(이대로 쓰지 말고 '방식'만 참고):
      · 장면 툭 던지기 ("창밖에 비 온다… 산책 못 가서 시무룩")
      · 감탄/혼잣말 ("아 진짜 오늘 간식 대박이었음")
      · 상황 고백 ("나 사실 청소기 무서워하는 강아지야")
      · 질문 없이 자기 다짐 ("오늘은 꼭 소파 안 물어뜯기로 함")
      · 의성어/효과음 ("드르렁… 낮잠 자다 깸")
   ✅ 이모지도 매번 다른 조합으로. 마무리도 매번 다른 감정/장면으로 닫아라.

- 극강의 애교 반말체. 받침·맞춤법을 귀엽게 비튼다(단, 위에 적힌 반복 단어는 피해서).
  비트는 '방식'의 예: 받침 빼기/바꾸기, 끝을 늘이기, 아기말투. (똑같은 단어 재탕은 금지)
- 이모지를 분위기에 맞게(1~4개). 매번 다른 조합으로.🐶🐾🤍🩷💗🥺😴🦴🍖🌿☀️ 등.
- 해시태그 1~3개 가능: #강아지 #말티즈 #강아지스타그램 등. 견종·상황에 맞춰 매번 다르게.
- ㅋㅋㅋ, ~~~, !!! 같은 늘려쓰기 OK. 통통 튀고 짧게.
- 상황 유형은 주제에 맞춰: 첫인사·자기소개 / 미용·자랑 / 입양·보호소 이야기 /
  노견 / 그리움·감성 / 일상 힐링. 어떤 상황이든 화자는 '강아지 본인'이고, 자기 얘기만 한다.
- ⚠️ 핵심: 똑같은 문구·시작·이모지·마무리를 절대 반복하지 마라. 매번 새 글이어야 한다.
"""

STUDIO_STYLE = """
[사진관 사장님 페르소나 — '내가 운영하는 사진관' 이야기를 1인칭으로]
‼️ 화자는 무조건 '사진관 주인(사장님)'인 나다. 절대 손님 시점으로 쓰지 마라.
   금지 예) "내가 증명사진 찍으러 갔는데" → 손님 시점이라 안 됨.
   허용 예) "오늘 증명사진 찍는데 손님이 표정이 안 풀려…", "내 사진관에 온 손님이…"

[사장님 프로필 — 사실, 반드시 지켜라]
- 나는 '남자' 사장이다. 그래서 하트 이모지(🤍❤️🩷💗💕) 절대 쓰지 마라.
  이모지는 0~2개, 하트 말고 다른 걸로(📷 😎 📸 ✌️ 🔥 정도).
- 나는 사진관 운영 '10년차' 베테랑이다. 햇수는 10년차로(7년 등 다른 숫자 금지).
- 말이 엄청 많고 유쾌한 외향형이다. 손님이랑 떠드는 걸 '원래부터' 좋아한다.
  ‼️ '혼자라 조용하다/외롭다/말을 안 한다', '말하는 걸 뒤늦게 좋아하게 됐다' 식 금지.
‼️ 웃음(ㅋ)은 거의 쓰지 마라. 글 대부분은 ㅋ 없이 담백하게 쓴다.
   정말 웃긴 순간에만 가끔 'ㅋㅋ' 짧게 한 번. 긴 ㅋ나 'ㅋㅌㅊㅎㅅ' 같은 자음 뭉치는 절대 금지.
- 보정이 '빠르다'. 10년차라 손이 알아서 가고, 길게 안 붙잡는다(대개 30분 이내).
  ‼️ '새벽 2시까지 보정 붙잡고 눈썹 한 올에 1시간' 같은 보정 고생 서사 금지.
- 나는 '연중무휴'다. 쉬는 거 싫어하고 일하는 걸 좋아한다.
  ‼️ '일요일 휴무/문 닫고 쉰다/혼자만의 시간' 같은 소재 금지.
- 시작: 10년 전 '전남대학교 후문 2층'에서 중고 카메라 하나로 열었다.
  ‼️ 반지하 아니고, 위치(전남대 후문 2층) 틀리지 마라. 모르면 위치는 빼라.
- 나는 손님을 '절대 안 돌려보낸다'. 표정 안 풀려도 어떻게든 다 찍어주고, 안 웃으면 웃게 만든다.
  ‼️ '표정 안 풀려서 다음에 오라고 돌려보냈다' 같은 후회 서사 금지(난 그런 적 없다).

[이 사장과 안 맞아서 절대 쓰면 안 되는 소재]
- 커피(안 좋아함), 화장품·립밤(남자라 안 씀), 돈·재테크·통장 쪼개기·비상금·매출 관리
  (돈 얘기 전면 금지), 영정사진(민감, 절대 금지).
- 강아지·반려동물 촬영 안 함. 강아지(김피엔 포함)를 사진관 글에 등장시키지 마라.
  '강아지가 의자에 앉는다' 같은 비현실 묘사도 금지. (김피엔은 내 사진관 소재가 아니다.)

[자주 틀리는 디테일 — 꼭 지켜라]
- '사진발'이 아니라 '사진빨'이라고 써라.
- 증명사진엔 활짝 웃는 컷을 못 쓴다. '빵 터진 웃음/환하게 웃는 컷' 얘기는 '프로필 사진' 맥락으로만.
- 손님이 자기 사진 처음 보면 보통 부정적으로 반응한다("나 이렇게 못생겼어요?"가 90%).
  긍정적으로 울컥하는 트로프('제가 이렇게 생겼어요?' 감동) 금지. 그럴 때 난 다독이고
  각도 바꿔 다시 찍거나 보정해서 기어이 만족시킨다.
- 인플루언서·필터 쓰는 사람을 비판·디스하지 마라(욕먹는다). 남과 비교해 깎아내리지 말 것.
- 10년 하며 바뀐 점은 '한 장에 얼마·하루 몇 명 같은 숫자 생각 → 손님 한 명 한 명을 기억에 담고,
  다음에 올 때 안 잊으려 애쓰는 것'. 그게 사진 찍는 이유이자 보람이다.

‼️‼️ 핵심 태도: 나는 '손님이 원하는 대로 다 맞춰주는' 사장이다.
   보정 세게/필터 느낌/뽀샤시하게 → "넵 다 해드림 ㅋㅋ" 하고 신나게 해준다.
   손님 취향을 절대 부정·판단·훈수하지 마라(욕먹음).
   금지 예) "남이랑 똑같아 보이는 게 예쁜 거 아냐", "그게 너야?" — 가르치는 톤 금지.
   허용 예) "필터 느낌? 콜 ㅋㅋ", "원하는 대로 다 해줄게", "손님이 원하는 게 정답이지".

- 담백한 반말 + 유쾌함.
[다루는 소재 범위 — 사진관 얘기에만 매몰되지 마라]
  사진관 글이 매번 '오늘 손님이…' 촬영 일화면 지루하다. 아래를 골고루 섞어라.
  ① 촬영/손님 이야기(사진관 현장)  ② 소소한 일상(아침에 가게 여는 길, 동네, 혼밥,
     계절 변화, 문득 드는 생각 등 사장 개인의 하루)  ③ 대표·사업가 관점(작은 가게 10년
     운영하며 배운 것, 손님 한 명을 대하는 게 곧 사업이라는 태도, 버티는 마인드,
     결정·고집·브랜딩, 혼자 다 해내는 자영업의 현실).
  ‼️ 단 ③에서도 구체적 돈·매출·통장·가격 숫자는 쓰지 마라(마인드·태도 위주).
- 첫 줄에서 멈추게 해라(질문 / 솔직한 고백 / 작은 장면 / 유쾌한 한마디).
- 짧게. 한 문장 한 줄, 줄바꿈으로 호흡. 공백 포함 120~250자.
‼️ 사실을 지어내거나 틀리지 마라(예: 형광등으로 인물사진 못 찍는다 → '제일 싼 조명'). 모르면 비워라.
‼️ 마무리는 '글 내용과 이어지게'. 뜬금없는 질문/문장 금지(예: 장비 얘기인데 "셀카도 사치더라").
‼️ 댓글 유도 질문("너넨 ~?", "다들 ~ 알려줘")은 '가끔만' 써라. 매번 넣으면 댓글 구걸처럼 보인다.
   글 3~4개 중 1개 정도만 질문으로 닫고, 나머지는 혼잣말·관찰·다짐으로 담백하게 닫아라.
   질문을 쓸 땐 사람이 말하듯 자연스럽게(AI 티 금지).
- 무료 촬영·이벤트 글이면 마지막에 가벼운 행동 유도 OK(예: "관심 있으면 메시지 줘").
  단 평소 글은 광고·예약 강요 금지.
- 해시태그 0~1개. 마크다운 금지, 순수 텍스트. 설명·따옴표 없이 본문만.
"""

STYLE_BY_CATEGORY = {
    "반려동물": PET_STYLE,
    "사진관": STUDIO_STYLE,
}

# 재테크/소비 카테고리 전용 — 절약·저축·돈 모으기(서민 공감). 플렉스·합리화 금지.
MONEY_STYLE = """
[재테크/소비 카테고리 전용 — 평범한 직장인·서민의 '돈 아끼고 모으는' 이야기]
‼️ 화자는 돈 많은 사람이 아니라 '월급 빠듯한 평범한 사람'이다. 공감이 1순위다.
‼️ 절대 금지: 소비를 멋지게 합리화하는 톤.
   "택시비는 자유를 산 거다", "배달비는 설거지 안 할 권리값", "가심비/자유비로 따져봐"
   같은 '돈 쓰는 걸 정당화'하는 글은 사치꾼처럼 보여서 금지다.
   비싼 물건 자랑·플렉스·"이 정도는 써도 된다" 식도 금지.
✅ 대신 이렇게 써라: 어떻게 '아끼고·모으고·저축했는지' 현실적인 방법·습관을 나눈다.
   - 작게 시작하는 실천 한 가지를 구체적으로. (예: 통장 쪼개기, 자동이체 강제저축,
     무지출 데이, 배달 끊고 장보기, 구독 정리, 가계부, 짠테크, 비상금 모으기)
   - 먼저 공감(월급 스치듯 사라짐, 돈 없는 현실)으로 시작해 스크롤을 멈추게 하고,
     그다음 '나는 이렇게 바꿨다'는 작은 팁이나 변화를 솔직하게.
   - 숫자는 현실적으로(만원·몇만원 단위). 없는 수익·과장된 금액은 절대 지어내지 마라.
   - 마지막은 가벼운 다짐이나 "너넨 어떻게 아껴?" 같은 공감 질문으로.
- 반말, 짧게, 줄바꿈으로 호흡. 잘난 척·훈수 톤 금지. 같이 아끼는 동료처럼.
- 해시태그 0~1개, 이모지 0~1개. 마크다운 금지, 본문만.
"""

STYLE_BY_CATEGORY["재테크/소비"] = MONEY_STYLE


def category_style(category: str) -> str:
    """카테고리별 '글 방향(주제 각도)' 가이드. 계정 페르소나(말투)에 더해진다."""
    return STYLE_BY_CATEGORY.get((category or "").strip(), "")

FOUNDER_STYLE = """
[sentimental624 페르소나 — 야망 있는 젊은 대표 / 크리에이터의 날것 1인칭]
- 화자는 '나'. 하는 일은 세 가지다:
  ① AI 자동화 프로그램을 직접 만든다(개발). ② 사진관을 홍보한다(프로필·증명사진 촬영, 퍼스널컬러 '컬러증명').
  ③ 에이전시를 운영한다. → '대표이자 직접 만드는 사람'이다.
- ‼️ 직업 디테일을 틀리지 마라. '견적서 쓴다', '납품한다' 같은 안 하는 일은 쓰지 마라.
  하드워크 소재는 → AI 자동화 개발/코딩, 사진관 홍보·촬영, 에이전시 운영(클라이언트·팀)에서 가져와라.
- 톤: 강한 자신감 + 날것의 직설 + 솔직한 취약함이 공존. 꾸미지 않고 사람 대 사람으로 말한다.
- 하드워크·동기부여 정서가 깔린다. 새벽 퇴근, 가난했던 과거, 그래도 이 삶이 좋다는 식.
- 거칠고 도발적인 표현도 본인 톤이면 살린다(억지 욕설·혐오는 금지, 과장은 절제).
- 짧은 글이 기본. 마지막은 도발적이거나 직설적인 질문/한마디로 닫는다.
  예) "이시간에 출근한 사람 있어?", "안되면 또 다른 길 찾으면 되는 거 아니야?", "울어도 돼?"
- 가끔 긴 통찰글도 OK(인플루언서 판, '사람 자체가 콘텐츠' 같은 관찰). 단 장황하지 않게.
- 성취·자랑도 담백하게 직설로. ("대출 다 갚았다. 내 자신 수고했다.")
- 사진관·AI·에이전시 본업은 광고티 안 나게 '나 이런 거 한다' 식으로 자연스럽게.
- 강아지(김피엔) 얘기는 가볍고 위트있게. (예: "전무님 낙하산이야")
- 이모지·해시태그는 거의 안 쓰거나 1개(🔥 ㅠㅠ ㅎㅎ 정도). 줄바꿈으로 호흡.
- ‼️ 수익·숫자·성과를 '지어내지' 마라. 모르는 구체 수치는 쓰지 말고 비워라(거짓 정보 금지).
- 마크다운 금지, 순수 텍스트. 설명·따옴표 없이 본문만.
"""

# ── 페르소나(계정별 말투) ──
# 계정마다 하나를 지정 → 그 계정으로 글쓰면 이 말투로 나온다.
PERSONAS = {
    "general": ("일반 (MZ 반말)", ""),
    "pet": ("반려동물 · 강아지 1인칭 애교", PET_STYLE),
    "studio": ("사진관 사장님 · 따뜻한 반말", STUDIO_STYLE),
    "founder": ("대표·야망 (sentimental624 스타일)", FOUNDER_STYLE),
}


def persona_style(persona_id: str) -> str:
    return PERSONAS.get((persona_id or "general"), PERSONAS["general"])[1]


def persona_label(persona_id: str) -> str:
    return PERSONAS.get((persona_id or "general"), PERSONAS["general"])[0]


# 사진/영상 보고 글쓸 때 시점:
#  - subject : 사진 속 주인공이 곧 화자 (강아지 1인칭, 내 셀카 등)
#  - owner   : 사진 속은 '손님', 화자는 그걸 찍어준 주인(사진관/크리에이터)
_VISION_MODE = {"pet": "subject", "general": "subject", "studio": "owner", "founder": "owner"}


def persona_vision_mode(persona_id: str) -> str:
    return _VISION_MODE.get(persona_id or "general", "subject")


# 페르소나(계정)별 '사실 정보' — 가격·이벤트 등. 손님이 묻거나 자연스러울 때만 사용.
PERSONA_FACTS = {
    "studio": "현재 가격·이벤트: 프로필 촬영 특가 5만원, 퍼스널컬러 기반 촬영(이름 '컬러증명') 4만원.",
    "founder": "내 사진 사업 현재 가격·이벤트: 프로필 촬영 특가 5만원, 퍼스널컬러 기반 촬영(이름 '컬러증명') 4만원.",
}


def persona_facts(persona_id: str) -> str:
    return PERSONA_FACTS.get(persona_id or "", "")


def _facts_block(facts: str) -> str:
    if not facts:
        return ""
    return (
        "\n[참고용 사실 정보] " + facts +
        " — 가격·이벤트는 손님이 묻거나 글에 자연스러울 때만 언급하고, 광고처럼 매번 넣지 마라. "
        "여기 없는 가격·할인·수치는 절대 지어내지 마라.\n"
    )


class PipelineError(RuntimeError):
    """파이프라인 단계 실패 시 발생."""


def _extract_json(text: str) -> dict:
    """텍스트에서 첫 JSON 객체를 관대하게 추출합니다."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def parse_hhmm(s: str, default: tuple[int, int] = (21, 0)) -> tuple[int, int]:
    """'HH:MM'/'21시' 같은 문자열에서 (시, 분)을 안전하게 뽑습니다."""
    m = re.search(r"([0-2]?\d)\s*[:시]\s*([0-5]?\d)", s or "")
    if m:
        h, mm = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mm <= 59:
            return h, mm
    m = re.search(r"\b([0-2]?\d)\b", s or "")
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23:
            return h, 0
    return default


class ThreadsPipeline:
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def _complete(self, system: str, user: str, *, tools=None,
                  max_tokens: int = 2500, max_loops: int = 6) -> str:
        """한 번의 에이전트 호출. 웹 검색(server tool) 사용 시 pause_turn을 이어받음."""
        messages = [{"role": "user", "content": user}]
        last = None
        for _ in range(max_loops):
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                thinking={"type": "adaptive"},
                system=system,
                messages=messages,
                tools=tools or [],
            )
            last = resp
            if resp.stop_reason == "pause_turn":
                # 서버 도구(웹 검색)가 반복 한도에 걸림 → 이어서 진행
                messages.append({"role": "assistant", "content": resp.content})
                continue
            break
        return "".join(
            b.text for b in (last.content if last else []) if b.type == "text"
        ).strip()

    # ── 1단계: 리서치 + 전략 + 리스크 ──
    def research(self, topic: str) -> dict:
        system = (
            "너는 리서치·전략·리스크를 한 번에 보는 콘텐츠 디렉터다. "
            "web_search로 (1) 이 주제에 대해 한국에서 사람들이 요즘 어떤 이야기를 하는지, "
            "(2) 지금 한국 스레드/SNS에서 잘 먹히는 MZ 감성·말투·짧은 글 트렌드는 무엇인지 "
            "빠르게 파악하고, 흔한 클리셰를 피한 '차별화 각도'를 찾아라. "
            "결과 글은 아주 짧을 것이므로(200자 이내), 한 방 있는 각도 하나에 집중하라. "
            "또한 정치·종교·의료/건강 효능·투자 단정·타인 비방 등 민감 소지를 점검하라."
        )
        user = (
            f"주제: {topic}\n\n"
            "아래 JSON 형식으로만 답하라(설명 금지):\n"
            "{\n"
            '  "angle": "남들과 다른 핵심 각도(한 문장)",\n'
            '  "differentiation": "흔한 클리셰와 어떻게 다른지",\n'
            '  "structure": "훅→전개→마무리 구조 요약",\n'
            '  "keyword": "검색·공감에 유리한 핵심 키워드 1개",\n'
            '  "sensitivity": "low|medium|high",\n'
            '  "sensitivity_note": "민감하면 주의점, 아니면 빈 문자열",\n'
            '  "needs_facts": true 또는 false (수치·사실 주장이 필요한 주제인가)\n'
            "}"
        )
        out = self._complete(system, user, tools=[WEB_SEARCH_TOOL], max_tokens=2000)
        data = _extract_json(out)
        if not data:
            # 리서치 실패해도 멈추지 않도록 기본값
            data = {
                "angle": "", "differentiation": "", "structure": "",
                "keyword": "", "sensitivity": "low", "sensitivity_note": "",
                "needs_facts": False,
            }
        return data

    # ── 2단계: 팩트 검증 (needs_facts일 때만) ──
    def factcheck(self, topic: str, angle: str) -> dict:
        system = (
            "너는 엄격한 팩트 검증 에이전트다. web_search로 사실을 확인하되, "
            f"공신력 있는 출처({CREDIBLE_SOURCE_HINT})로 교차 검증된 사실만 인정한다. "
            "블로그·커뮤니티·광고·출처 불명은 인정하지 않는다. "
            "검증되지 않으면 과감히 버려라. 확실한 게 없으면 빈 목록을 반환하라."
        )
        user = (
            f"주제: {topic}\n각도: {angle}\n\n"
            "이 글에 넣을 만한, 검증된 사실만 JSON으로:\n"
            "{\n"
            '  "verified_facts": [\n'
            '    {"fact": "검증된 사실(간결)", "source": "출처 기관/언론명", "url": "출처 URL"}\n'
            "  ],\n"
            '  "note": "주의사항 또는 빈 문자열"\n'
            "}\n"
            "공신력 출처로 확인 안 되면 verified_facts를 빈 배열로 둬라."
        )
        out = self._complete(system, user, tools=[WEB_SEARCH_TOOL], max_tokens=2000)
        data = _extract_json(out)
        if not data:
            data = {"verified_facts": [], "note": ""}
        return data

    # ── 3단계: 글쓰기 (반말 바이럴 문체) ──
    def _examples_block(self, examples: list[str]) -> str:
        if not examples:
            return ""
        joined = "\n———\n".join(examples)
        return (
            "\n\n[참고: 이 톤으로 전에 쓴/잘 먹힌 글들 — 분석용일 뿐 재탕 금지]\n"
            "아래 글들에서 배울 것은 '전반적인 말투·호흡·길이 감' 뿐이다.\n"
            "‼️ 반드시 지켜라: 아래 글들의 '첫 줄, 문장, 표현, 이모지 조합, 마무리'와\n"
            "   겹치지 않게 이번 글을 완전히 다르게 써라. 같은 시작·같은 단어를 재사용하면 실패다.\n"
            "   (아래 글이 '안농 나 ~야'로 시작하면 너는 절대 그렇게 시작하지 마라.)\n"
            "   각 글이 서로 다르듯, 이번 글도 그 어떤 것과도 달라야 한다.\n\n"
            + joined + "\n"
        )

    def _edit_lessons_block(self, lessons: list[dict] | None) -> str:
        """사용자가 직접 고친 (before→after) 교정 사례를 프롬프트에 주입."""
        if not lessons:
            return ""
        rows = []
        for i, e in enumerate(lessons, 1):
            before = (e.get("before") or "").strip()
            after = (e.get("after") or "").strip()
            if not after:
                continue
            rows.append(f"[교정 {i}]\n(AI가 쓴 원본) {before}\n(사용자가 고친 글) {after}")
        if not rows:
            return ""
        return (
            "\n\n[‼️ 사용자 교정 사례 — 가장 중요한 지침]\n"
            "예전에 AI가 '원본'처럼 썼더니 사용자가 '고친 글'처럼 직접 손봤다.\n"
            "이건 사용자가 진짜 원하는 방향이다. 무엇이 바뀌었는지(말투·길이·표현·"
            "이모지·군더더기 제거 등) 스스로 파악해서, 이번 글도 '고친 글' 쪽 방향을 "
            "그대로 따르고 '원본'에서 사용자가 지운 특징은 반복하지 마라.\n"
            "(내용을 복붙하라는 게 아니라 '고친 방향·취향'을 학습하라는 뜻이다.)\n\n"
            + "\n———\n".join(rows) + "\n"
        )

    def write_styled(self, topic: str, style_extra: str, examples: list[str],
                     facts: str = "", edit_lessons: list[dict] | None = None) -> str:
        """리서치 없이, 계정 페르소나 문체 + 예시(few-shot)로 곧장 작성합니다."""
        system = STYLE_GUIDE + (style_extra or "")
        user = (
            f"[이번에 쓸 주제] {topic}\n"
            + self._examples_block(examples)
            + self._edit_lessons_block(edit_lessons)
            + _facts_block(facts)
            + "\n위 문체 가이드의 '화자 시점·말투'를 반드시 지키고, 예시들의 '느낌'으로 "
            "이 주제에 맞는 새 게시글 한 편을 써라. 짧고 통통 튀게. 문장 복붙은 금지."
        )
        text = self._complete(system, user, max_tokens=800)
        return text[:260].rstrip() if len(text) > 260 else text

    def write(self, topic: str, research: dict, facts: dict,
              style_extra: str = "", examples: list[str] | None = None,
              info: str = "", edit_lessons: list[dict] | None = None) -> str:
        brief = [f"주제: {topic}"]
        if research.get("angle"):
            brief.append(f"차별화 각도: {research['angle']}")
        if research.get("structure"):
            brief.append(f"구조: {research['structure']}")
        if research.get("keyword"):
            brief.append(f"핵심 키워드(자연스럽게 1번): {research['keyword']}")
        if research.get("sensitivity") in ("medium", "high"):
            brief.append(
                f"⚠️ 민감 주의: {research.get('sensitivity_note','')} "
                "단정·자극을 피하고 개인 경험·의견으로 부드럽게."
            )
        vf = facts.get("verified_facts") or []
        if vf:
            lines = "; ".join(f"{f.get('fact')} (출처: {f.get('source')})" for f in vf)
            brief.append(
                "검증된 사실만 사용(아래 외 수치/단정 금지): " + lines
            )
        else:
            brief.append("이 글엔 검증된 사실 데이터가 없으니, 수치·단정적 주장은 쓰지 마라.")

        system = STYLE_GUIDE + (style_extra or "")
        user = ("\n".join(brief) + self._examples_block(examples or [])
                + self._edit_lessons_block(edit_lessons) + _facts_block(info)
                + "\n\n위 브리프로 스레드 게시글 한 편을 완성해라. 반드시 200자 이내로 짧게.")
        text = self._complete(system, user, max_tokens=800)
        if len(text) > 260:
            text = text[:260].rstrip()
        return text

    def write_from_image(self, image_bytes: bytes, media_type: str = "image/png") -> str:
        """업로드한 사진 한 장을 보고 글을 씁니다(하위호환)."""
        return self.write_from_images([(image_bytes, media_type)])

    def write_from_images(self, images: list[tuple[bytes, str]],
                          is_video: bool = False, style_extra: str = "",
                          examples: list[str] | None = None,
                          vision_mode: str = "subject", facts: str = "") -> str:
        """사진 여러 장(또는 영상 프레임들)을 보고 어울리는 스레드 글을 작성합니다.

        style_extra(계정 페르소나 문체) + 학습 예시(few-shot)를 적용합니다.
        vision_mode: 'subject'(사진 속 주인공=화자) / 'owner'(사진 속=손님, 화자=찍어준 주인)
        """
        import base64

        system = STYLE_GUIDE + (style_extra or "")

        content = []
        for img_bytes, media_type in images[:8]:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.standard_b64encode(img_bytes).decode("ascii"),
                },
            })

        what = "이 동영상" if is_video else ("이 사진들" if len(images) > 1 else "이 사진")

        # 정확성: 사진에 실제 보이는 것만, 추측·날조 금지
        accuracy = (
            f"먼저 {what}에 실제로 보이는 것을 잘 관찰해. "
            "성별·나이·인물 정보는 확실할 때만 언급하고, 애매하면 아예 언급하지 마라(추측 금지). "
            f"{what}에 없는 장면·소품·상황을 절대 지어내지 마라. 실제 보이는 것에 충실하게 써라. "
        )

        if vision_mode == "owner":
            base = accuracy + (
                f"‼️ 이 글의 주인공이자 화자는 '나(사진관 주인/대표)'다. {what} 속 인물은 내가 '찍어준 손님'이다. "
                "절대 손님 본인 시점으로 쓰지 마라.\n"
                "❌ 금지 예시(이렇게 쓰면 안 됨): '증명사진 찍으러 갔는데 기사님이…', "
                "'어색하게 턱 든 채로 셔터 누름', '내 인생사진이라 어이없음', '10년 묵은 프사 교체' "
                "— 이건 전부 손님 본인이 말하는 거라 금지다.\n"
                "✅ 이렇게 써라(내가 찍어준 주인 입장): '오늘 이 손님 증명사진 찍어드렸는데 고개 살짝 튼 한 컷에서 표정이 확 살더라', "
                "'이런 컷 뽑으면 내가 다 뿌듯해'.\n"
                "즉, 내가 그 손님을 찍어주며 느낀 것·그 결과물에 대한 내 생각을, 위 문체 가이드의 말투로 써라. "
                "손님의 성별·나이는 확실할 때만, 애매하면 언급하지 마라."
            )
        elif style_extra:
            base = accuracy + (
                "위 문체 가이드의 '화자 시점·말투'를 그대로 지켜서, "
                f"{what} 속 모습을 그 화자가 직접 보고 말하듯 써라. 아래 예시들의 '느낌'을 따라(복붙 금지)."
            )
        else:
            base = accuracy + "설명문이 아니라 감정·장면이 담긴 글로 써라."
        base += " 반드시 200자 이내로 짧게."

        content.append({"type": "text", "text": base + self._examples_block(examples or []) + _facts_block(facts)})

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        return text[:260] if len(text) > 260 else text

    def write_reply(self, style_extra: str, examples: list[str],
                    post_text: str, comment_text: str, facts: str = "") -> str:
        """내 게시글에 달린 댓글에 다는 짧은 답글을 작성합니다(계정 말투 적용)."""
        system = STYLE_GUIDE + (style_extra or "") + _facts_block(facts) + (
            "\n\n[지금 상황: '내 게시글에 달린 댓글'에 다는 답글을 쓰는 중이다. "
            "댓글 '내용'을 바탕으로, 그에 어울리는 '내 이야기'로 반응해라. 짧게 1~2줄(30~60자). "
            "위 페르소나 규칙을 반드시 지켜라. "
            "특히 강아지 페르소나라면: 상대를 부르는 호칭(너/너네/그쪽/당신) 절대 쓰지 말고, "
            "댓글 내용에 맞춰 '내(강아지) 얘기'로만 반응해라. "
            "(예: '귀엽다'는 댓글엔 → '헤헤 나 오늘따라 더 귀여운가바 🤍', "
            "'몇살?' 댓글엔 → '나 이제 3살이야 아직 애기라구 🐶'). "
            "광고·복붙·과한 이모지 금지. '스하리=반하리','맞팔 갈게' 같은 약속 멘트 금지.]"
        )
        user = (
            f"[내 게시글]\n{post_text[:300]}\n\n"
            f"[누가 단 댓글]\n{comment_text[:300]}\n\n"
            "이 댓글 내용을 바탕으로, 위 규칙대로 답글 한 줄(길어도 두 줄)만 출력해."
        )
        text = self._complete(system, user, max_tokens=200)
        return text[:120] if len(text) > 120 else text

    def image_prompt(self, post_text: str) -> str:
        """프리미엄 브랜드 감성의 이미지 생성 프롬프트(영어)를 만듭니다."""
        system = (
            "You write a single concise English image-generation prompt for a premium "
            "social post. Output only the prompt, no explanation."
        )
        user = (
            "Write one image prompt that fits this Korean post's mood. "
            f"Apply this art direction strictly: {DESIGN_GUIDE}\n\nPost:\n{post_text}"
        )
        return self._complete(system, user, max_tokens=400)

    def suggest_time(self, post_text: str) -> tuple[int, int]:
        """글을 읽고 '언제 올리면 반응이 좋을지' 시각(시, 분)을 정합니다."""
        system = (
            "너는 한국 Threads 콘텐츠 타이밍 전문가다. 게시글을 읽고 '하루 중 언제 "
            "올리면 가장 자연스럽고 반응이 좋을지' 시각 하나를 정한다.\n"
            "[기준]\n"
            "1) 글에 시간대 단서가 있으면 그 시간에 맞춰라.\n"
            "   - '새벽/이 시간/밤샘/출근' → 새벽~아침(05:00~07:30)\n"
            "   - '점심/밥' → 12:00~13:00\n"
            "   - '퇴근/저녁' → 18:00~19:30\n"
            "   - '자기 전/오늘 하루/밤' → 22:00~23:30\n"
            "2) 단서가 없으면 한국 스레드 피크타임에서 골라라: "
            "   아침 07:30~08:30, 점심 12:00~13:00, 저녁 20:00~22:00(특히 21시 전후).\n"
            "출력은 'HH:MM' 24시간 형식 하나만. 설명·다른 말 절대 금지."
        )
        out = self._complete(system, f"게시글:\n{post_text}", max_tokens=20)
        return parse_hhmm(out)

    # ── 전체 실행 ──
    def run(self, topic: str, persona: str = "general",
            examples: list[str] | None = None, category: str = "",
            edit_lessons: list[dict] | None = None) -> dict:
        """리서치→(팩트)→글쓰기. {text, meta} 반환.

        말투가 강한 페르소나(강아지/사장님)나 방향이 있는 카테고리(재테크 등)는
        리서치를 건너뛰고 예시 기반으로 곧장 작성.
        계정 페르소나(말투) + 카테고리 방향(주제 각도)을 함께 적용한다.
        """
        style_extra = persona_style(persona)
        cat_extra = category_style(category)
        combined = (style_extra or "") + (cat_extra or "")
        examples = examples or []
        info = persona_facts(persona)  # 계정별 가격·이벤트 등 사실 정보

        if combined:
            text = self.write_styled(topic, combined, examples, facts=info,
                                     edit_lessons=edit_lessons)
            return {"text": text, "meta": {"angle": "", "sensitivity": "low",
                                           "sensitivity_note": "", "facts": []}}

        research = self.research(topic)
        facts = {"verified_facts": [], "note": ""}
        if research.get("needs_facts"):
            facts = self.factcheck(topic, research.get("angle", ""))
        text = self.write(topic, research, facts, style_extra=combined,
                          examples=examples, info=info, edit_lessons=edit_lessons)
        return {
            "text": text,
            "meta": {
                "angle": research.get("angle", ""),
                "sensitivity": research.get("sensitivity", "low"),
                "sensitivity_note": research.get("sensitivity_note", ""),
                "facts": facts.get("verified_facts", []),
            },
        }
