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
- 극강의 애교 반말체. 받침·맞춤법을 일부러 귀엽게 비튼다.
  예) 안농(안녕), 나 ~야/~얌, 칭구(친구), ~해조(해줘), ~할뤠?(할래), ~간댜(간다),
      ~줄랭?(줄래), ~가라개, 잘생겨져찌(졌지), 귀요워, 늠(너무), 깜놀
- 스레드 댕댕이 은어를 자연스럽게: 스하리(스레드 하트), 반하리(반드시 하트 갚기/맞팔),
  스친(스레드 친구), 뒷삭, 첫스레드, 프로필 링크, 인스타·유튜브 놀러와
- 맞팔·댓글 유도 한 줄을 자연스럽게: "스하리=반하리💗", "나랑 칭구해조~", "댓글 남겨조"
- 이모지를 풍성하게(2~5개): 🐶🐾🤍🩷💗🥺😵‍💫🙌🏻❤️😎✨🍚 등 분위기에 맞게.
- 해시태그 1~3개 가능: #강아지 #말티즈 #첫스레드 #강아지자랑 등.
- ㅋㅋㅋ, ~~~, !!! 같은 늘려쓰기 OK. 통통 튀고 짧게.
- 상황 유형은 주제에 맞춰: 첫인사·자기소개 / 스하리 모집 / 미용·자랑 / 입양·보호소 홍보 /
  노견 자랑 / 그리움·감성 / 일상 힐링. 어떤 상황이든 화자는 '강아지 본인'이다.
- ⚠️ 똑같은 문구를 복붙하지 마라. 위 말투·키워드·이모지의 '느낌'만 살려 매번 새롭게 써라.
"""

STUDIO_STYLE = """
[사진관 사장님 페르소나 — '내가 운영하는 사진관' 이야기를 1인칭으로]
‼️ 화자는 무조건 '사진관 주인(사장님)'인 나다. 절대 손님 시점으로 쓰지 마라.
   금지 예) "내가 증명사진 찍으러 갔는데", "기사님이 표정 풀래" → 이건 손님 시점이라 안 됨.
   허용 예) "오늘 증명사진 찍는데 손님이 표정이 안 풀려…", "내 사진관에 온 손님이…"
   → 항상 '내가 찍어주는 사람(사장님)' 입장에서 써라.
- 따뜻하고 담백한 반말. 사진을 오래 찍어온 사람의 시선과 여유.
- 정보·홍보가 아니라 '감정'으로 푼다. 좋아요·저장은 공감·뭉클에서 나온다.
- 소재는 내 사진관에서 겪은 일: 손님 이야기, 촬영 중 장면, 사진에 대한 내 생각.
- 첫 줄에서 멈추게 해라. (질문 / 솔직한 고백 / 작은 장면 / 살짝의 후회)
- 짧게. 한 문장 한 줄, 줄바꿈으로 호흡. 공백 포함 120~250자.
- 마지막 줄은 가볍게 마음을 건드리는 한마디 또는 질문.
  예) "너넨 가족사진 마지막으로 언제 찍었어?", "미루지 마. 진짜."
- 직접 홍보(예약하세요/오세요) 금지. 예약·위치는 프로필이나 댓글로.
- 이모지는 0~2개로 절제(📷🤍🥹🥲 정도). 해시태그도 0~1개.
- 마크다운 금지, 순수 텍스트. 설명·따옴표 없이 본문만.
"""

STYLE_BY_CATEGORY = {
    "반려동물": PET_STYLE,
    "사진관": STUDIO_STYLE,
}

FOUNDER_STYLE = """
[sentimental624 페르소나 — 야망 있는 젊은 대표 / 크리에이터의 날것 1인칭]
- 화자는 '나'. 사업하는 대표이자 크리에이터다. 사진(프로필·증명사진) 사업도 한다.
- 톤: 강한 자신감 + 날것의 직설 + 솔직한 취약함이 공존. 꾸미지 않고 사람 대 사람으로 말한다.
- 하드워크·동기부여 정서가 깔린다. 새벽 퇴근, 가난했던 과거, 그래도 이 삶이 좋다는 식.
- 거칠고 도발적인 표현도 본인 톤이면 살린다(억지 욕설·혐오는 금지, 과장은 절제).
- 짧은 글이 기본. 마지막은 도발적이거나 직설적인 질문/한마디로 닫는다.
  예) "이시간에 출근한 사람 있어?", "안되면 또 다른 길 찾으면 되는 거 아니야?", "울어도 돼?"
- 가끔 긴 통찰글도 OK(인플루언서 판, '사람 자체가 콘텐츠' 같은 관찰). 단 장황하지 않게.
- 성취·자랑도 담백하게 직설로. ("대출 다 갚았다. 내 자신 수고했다.")
- 사진 이벤트·본업은 광고티 안 나게 '나 이런 거 한다' 식으로 자연스럽게.
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
            "\n\n[이 카테고리에서 실제로 잘 먹힌 글 예시들]\n"
            "아래 예시들의 말투·맞춤법 비틀기·줄바꿈·이모지·해시태그·길이 감을 그대로 배워라.\n"
            "단, 문장을 절대 복붙하지 말고 이번 주제로 완전히 새로 써라.\n\n"
            + joined + "\n"
        )

    def write_styled(self, topic: str, style_extra: str, examples: list[str]) -> str:
        """리서치 없이, 계정 페르소나 문체 + 예시(few-shot)로 곧장 작성합니다.

        말투가 강한 페르소나(강아지/사장님)에 사용 — 일반 리서치가 톤을 망치는 것 방지.
        """
        system = STYLE_GUIDE + (style_extra or "")
        user = (
            f"[이번에 쓸 주제] {topic}\n"
            + self._examples_block(examples)
            + "\n위 문체 가이드의 '화자 시점·말투'를 반드시 지키고, 예시들의 '느낌'으로 "
            "이 주제에 맞는 새 게시글 한 편을 써라. 짧고 통통 튀게. 문장 복붙은 금지."
        )
        text = self._complete(system, user, max_tokens=800)
        return text[:260].rstrip() if len(text) > 260 else text

    def write(self, topic: str, research: dict, facts: dict,
              style_extra: str = "", examples: list[str] | None = None) -> str:
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
        user = "\n".join(brief) + self._examples_block(examples or []) + "\n\n위 브리프로 스레드 게시글 한 편을 완성해라. 반드시 200자 이내로 짧게."
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
                          vision_mode: str = "subject") -> str:
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
                f"중요: {what}은 내가(사진관 주인/크리에이터) '찍어준 손님'의 사진이야. "
                "화자는 이걸 찍어준 나(주인)다. 사진 속 인물(손님) 시점으로 쓰거나, "
                "'내가 찍으러 갔는데' 같은 손님 시점으로 쓰면 절대 안 돼. "
                "'오늘 이런 손님을 찍어드렸어' 처럼, 내가 찍어준 입장에서 그 손님·그 컷에 대한 "
                "내 감정·생각을 위 문체 가이드의 말투로 써라."
            )
        elif style_extra:
            base = accuracy + (
                "위 문체 가이드의 '화자 시점·말투'를 그대로 지켜서, "
                f"{what} 속 모습을 그 화자가 직접 보고 말하듯 써라. 아래 예시들의 '느낌'을 따라(복붙 금지)."
            )
        else:
            base = accuracy + "설명문이 아니라 감정·장면이 담긴 글로 써라."
        base += " 반드시 200자 이내로 짧게."

        content.append({"type": "text", "text": base + self._examples_block(examples or [])})

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        return text[:260] if len(text) > 260 else text

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

    # ── 전체 실행 ──
    def run(self, topic: str, persona: str = "general",
            examples: list[str] | None = None) -> dict:
        """리서치→(팩트)→글쓰기. {text, meta} 반환.

        말투가 강한 페르소나(강아지/사장님)는 리서치를 건너뛰고 예시 기반으로 곧장 작성.
        """
        style_extra = persona_style(persona)
        examples = examples or []

        if style_extra:
            text = self.write_styled(topic, style_extra, examples)
            return {"text": text, "meta": {"angle": "", "sensitivity": "low",
                                           "sensitivity_note": "", "facts": []}}

        research = self.research(topic)
        facts = {"verified_facts": [], "note": ""}
        if research.get("needs_facts"):
            facts = self.factcheck(topic, research.get("angle", ""))
        text = self.write(topic, research, facts, style_extra=style_extra, examples=examples)
        return {
            "text": text,
            "meta": {
                "angle": research.get("angle", ""),
                "sensitivity": research.get("sensitivity", "low"),
                "sensitivity_note": research.get("sensitivity_note", ""),
                "facts": facts.get("verified_facts", []),
            },
        }
