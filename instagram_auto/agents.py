"""다중 에이전트 콘텐츠 파이프라인 (고급 생성 엔진).

하나의 LLM에 다 맡기지 않고, 역할을 나눈 에이전트가 순차로 콘텐츠를 고도화한다.

  1) 리서치(Research)   : 상위 노출 글 패턴 분석 + 차별화 포인트 (웹 검색 가능 시)
  2) 전략(Strategy)     : 조회수·저장 극대화 콘텐츠 구조 설계
  3) 팩트검증(FactCheck): 공신력 기관 출처만 인정, 검증 불가 주장 제거
  4) 카피(Copywriter)   : 인스타 말투 + 구텐베르크(블록) 형식 본문 작성
  5) SEO 편집(SEO)      : 제목·해시태그·캡션 검색 최적화
  6) 리스크(Risk)       : 민감 주제·저품질·노출저하 요인 감지 및 수정
  7) 디자인(Design)     : 트렌드 기반 테마/레이아웃 선택

웹 검색이 필요한 에이전트(리서치/팩트검증/SEO/디자인 트렌드)는 검색 가능한
LLM(예: Anthropic web_search, Gemini google_search grounding)이 있을 때 자동 수행되며,
없으면 모델 내장 지식으로 동작하고 audit 리포트에 '검색 미사용'을 표시한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import llm
from .config import Config
from .content import CardNews


@dataclass
class AgentReport:
    """각 에이전트의 산출/판단을 기록하는 감사 리포트."""
    steps: list[dict] = field(default_factory=list)
    web_search_used: bool = False
    risk_flags: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def log(self, agent: str, summary: str, data: dict | None = None):
        self.steps.append({"agent": agent, "summary": summary, "data": data or {}})


# --------------------------------------------------------------------------- #
# 웹 검색 (가능한 경우)
# --------------------------------------------------------------------------- #
def web_search(query: str, config: Config) -> str:
    """검색 가능한 LLM으로 웹 검색 요약을 반환. 불가 시 빈 문자열."""
    provider = config.caption_provider
    try:
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            msg = client.messages.create(
                model=config.caption_model,
                max_tokens=1024,
                tools=[{"type": "web_search_20250305", "name": "web_search",
                        "max_uses": 5}],
                messages=[{"role": "user", "content": query}],
            )
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        if provider == "gemini":
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=config.gemini_api_key)
            resp = client.models.generate_content(
                model=config.gemini_text_model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                ),
            )
            return resp.text or ""
    except Exception:
        return ""
    return ""


# --------------------------------------------------------------------------- #
# 개별 에이전트
# --------------------------------------------------------------------------- #
def research_agent(topic: str, config: Config, report: AgentReport) -> dict:
    """상위 노출 글 패턴 분석 + 차별화 포인트."""
    search = web_search(
        f"인스타그램 '{topic}' 관련 인기 카드뉴스/콘텐츠의 공통 구성과 "
        f"자주 다루는 소재, 그리고 사람들이 더 궁금해하지만 잘 안 다뤄지는 빈틈을 알려줘.",
        config,
    )
    if search:
        report.web_search_used = True
    sys = ("너는 콘텐츠 리서치 애널리스트다. 주어진 주제의 상위 노출 콘텐츠 패턴을 분석하고, "
           "남들이 안 다루는 '차별화 포인트' 3가지를 찾는다. JSON만 출력.\n"
           '{"common_patterns":["..."],"gaps":["..."],"differentiators":["..."]}')
    user = f"주제: {topic}\n\n[웹 검색 참고자료]\n{search[:2000] or '(검색 미사용 — 내장 지식 기반)'}"
    data = llm.complete_json(sys, user, config)
    report.log("research", f"차별화 포인트 {len(data.get('differentiators', []))}개 도출", data)
    return data


def strategy_agent(topic: str, research: dict, config: Config, report: AgentReport) -> dict:
    """조회수·저장 극대화 구조 설계."""
    sys = ("너는 인스타 콘텐츠 전략가다. 저장·공유·완독률을 높이는 카드뉴스 구조를 설계한다. "
           "후킹 표지, 본문 카드 흐름(논리 순서), 마무리 CTA, 그리고 '왜 이 구조가 조회수에 유리한지' "
           "근거를 제시한다. JSON만.\n"
           '{"angle":"콘텐츠 앵글","hook":"표지 후킹 컨셉","card_flow":["카드1 주제","..."],'
           '"cta":"마무리 CTA","why_it_works":"조회수 근거"}')
    user = f"주제: {topic}\n차별화 포인트: {json.dumps(research.get('differentiators', []), ensure_ascii=False)}"
    data = llm.complete_json(sys, user, config)
    report.log("strategy", f"앵글: {data.get('angle', '')[:40]}", data)
    return data


def factcheck_agent(topic: str, strategy: dict, config: Config, report: AgentReport) -> dict:
    """공신력 기관 출처만 인정, 검증 불가 주장 제거."""
    search = web_search(
        f"'{topic}'에 대해 한국의 공신력 있는 정부·공공기관(예: 금융감독원, 한국은행, 국세청, "
        f"국민연금공단, 예금보험공사 등)이 제공하는 정확한 사실과 최신 기준을 확인해줘. 출처 기관명 포함.",
        config,
    )
    if search:
        report.web_search_used = True
    sys = ("너는 팩트체커다. 공신력 있는 정부·공공·공인기관 출처만 신뢰한다. "
           "주제의 핵심 사실을 검증하고, 검증 가능한 사실/주의가 필요한 변동항목/근거 기관을 분류한다. "
           "수치·세율·한도처럼 바뀌는 값은 '기관 확인 필요'로 표시. JSON만.\n"
           '{"verified_facts":["..."],"volatile_items":["기관 확인 필요 항목"],'
           '"authoritative_sources":["기관명"]}')
    user = f"주제: {topic}\n구조: {json.dumps(strategy, ensure_ascii=False)[:1500]}\n\n[검색 참고]\n{search[:2000] or '(검색 미사용)'}"
    data = llm.complete_json(sys, user, config)
    report.sources += data.get("authoritative_sources", [])
    report.log("factcheck", f"검증 사실 {len(data.get('verified_facts', []))}건, "
                            f"변동항목 {len(data.get('volatile_items', []))}건", data)
    return data


def trend_brief(topic: str, config: Config, report: AgentReport) -> str:
    """말투/유행어·밈 + 디자인 트렌드 브리핑 (웹 검색 가능 시)."""
    search = web_search(
        f"요즘 인스타그램에서 유행하는 말투/유행어/밈과, '{topic}' 같은 정보형 콘텐츠에 어울리는 "
        f"최신 카드뉴스 디자인 트렌드(컬러·타이포·레이아웃)를 간단히 정리해줘.",
        config,
    )
    if search:
        report.web_search_used = True
    return search


def copywriter_agent(topic, strategy, facts, trend, config, report) -> dict:
    """인스타 말투 + 구텐베르크(블록) 형식 본문 작성."""
    sys = ("너는 인스타 카드뉴스 카피라이터다. 아래 규칙을 지켜 JSON으로만 출력한다.\n"
           "- 검증된 사실만 사용하고, 변동 항목은 단정하지 말고 '기관 확인'을 권한다.\n"
           "- 본문은 '구텐베르크 블록' 형식: 카드 하나당 1개 핵심 + 짧은 단락(2~3줄).\n"
           "- 인스타에서 자주 쓰는 친근한 말투. 과한 낚시는 금지(저품질·노출저하 위험).\n"
           "- 유행어/밈은 자연스러운 선에서 1~2개만 가볍게.\n"
           "- caption에는 저장/팔로우/공유 문구를 넣지 마라(시스템이 자동 추가). 대신 댓글을 부르는 "
           "comment_question(구체적 질문 한 줄)을 반드시 만든다.\n"
           '{"cover_title":"줄바꿈\\n가능","cover_subtitle":"...",'
           '"cards":[{"title":"...","body":"...\\n..."}],'
           '"closing_title":"...","closing_cta":"...","comment_question":"...","caption":"...","hashtags":["#..."]}')
    user = (f"주제: {topic}\n전략: {json.dumps(strategy, ensure_ascii=False)[:1200]}\n"
            f"검증사실: {json.dumps(facts.get('verified_facts', []), ensure_ascii=False)[:1200]}\n"
            f"변동항목(확인필요): {json.dumps(facts.get('volatile_items', []), ensure_ascii=False)[:600]}\n"
            f"트렌드/말투 참고: {(trend or '(없음)')[:800]}\n"
            f"근거 기관: {json.dumps(facts.get('authoritative_sources', []), ensure_ascii=False)}")
    data = llm.complete_json(sys, user, config)
    report.log("copywriter", "본문/캡션/해시태그 초안 작성", {"hashtags": data.get("hashtags", [])})
    return data


def seo_agent(draft: dict, config: Config, report: AgentReport) -> dict:
    """검색 최적화: 제목/해시태그/캡션 다듬기."""
    sys = ("너는 인스타 SEO 편집자다. 검색·탐색 노출을 높이도록 제목·캡션·해시태그를 최적화한다.\n"
           "- 제목: 검색 키워드 자연 포함 + 후킹 유지.\n"
           "- 해시태그: 대형/중형/소형(니치) 12~15개 믹스, 주제 무관/금지 태그 제외.\n"
           "- 캡션: 첫 줄 후킹 + 근거 기관 표기. (저장/팔로우 문구는 넣지 말 것 — 자동 추가됨)\n"
           "- comment_question은 더 답하고 싶게 다듬어 반드시 유지한다.\n"
           "원본 의미는 유지하되 최적화. JSON 동일 스키마(comment_question 포함)로만 출력.")
    user = json.dumps(draft, ensure_ascii=False)
    data = llm.complete_json(sys, user, config)
    report.log("seo", f"해시태그 {len(data.get('hashtags', []))}개로 최적화", None)
    return data


def risk_agent(draft: dict, config: Config, report: AgentReport) -> dict:
    """민감 주제·저품질·노출저하 요인 감지 및 수정 제안."""
    sys = ("너는 콘텐츠 리스크 심사관이다. 인스타 노출 저하/저품질/정책 위반 위험을 점검한다.\n"
           "점검: 단정적 투자권유·과장/낚시·의료/법률 단정·민감/혐오 표현·과도한 해시태그·"
           "스팸성 문구. 위험이 있으면 수정안을 반영해 동일 스키마로 출력하고, flags에 사유를 남긴다.\n"
           '출력: {"content":{...동일 스키마...},"flags":["..."]}')
    user = json.dumps(draft, ensure_ascii=False)
    data = llm.complete_json(sys, user, config)
    flags = data.get("flags", [])
    report.risk_flags += flags
    report.log("risk", f"리스크 플래그 {len(flags)}건 처리", {"flags": flags})
    return data.get("content", draft)


# --------------------------------------------------------------------------- #
# 오케스트레이터
# --------------------------------------------------------------------------- #
def generate_cardnews_agentic(
    topic: str, config: Config, tone: str = "친근하고 신뢰감 있는"
) -> tuple[CardNews, AgentReport]:
    """7개 에이전트를 순차 실행해 고급 카드뉴스를 생성한다."""
    report = AgentReport()

    research = research_agent(topic, config, report)
    strategy = strategy_agent(topic, research, config, report)
    facts = factcheck_agent(topic, strategy, config, report)
    trend = trend_brief(topic, config, report)
    draft = copywriter_agent(topic, strategy, facts, trend, config, report)
    draft = seo_agent(draft, config, report)
    draft = risk_agent(draft, config, report)

    cards = [{"title": str(c.get("title", "")).strip(),
              "body": str(c.get("body", "")).strip()} for c in draft.get("cards", [])]
    hashtags = []
    for t in draft.get("hashtags", []):
        t = str(t).strip().replace(" ", "")
        hashtags.append(t if t.startswith("#") else f"#{t}")

    cn = CardNews(
        cover_title=draft.get("cover_title", topic).strip(),
        cover_subtitle=draft.get("cover_subtitle", "").strip(),
        cards=cards,
        closing_title=draft.get("closing_title", "").strip(),
        closing_cta=draft.get("closing_cta", "저장하고 팔로우").strip(),
        caption=draft.get("caption", "").strip(),
        hashtags=hashtags,
        comment_question=draft.get("comment_question", "").strip(),
    )
    return cn, report
