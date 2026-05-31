"""1주차 카드뉴스 콘텐츠 기획서 PDF 생성기.

니치: 사회초년생 재테크 (@money.note)
제목·멘트·해시태그를 인스타 노출 최적화 관점으로 구성한다.

실행:  python scripts/build_week_plan_pdf.py
출력:  output/1주차_카드뉴스_기획서.pdf
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FONT_DIR = Path.home() / ".cache" / "instagram_auto" / "fonts"
pdfmetrics.registerFont(TTFont("Nanum", str(FONT_DIR / "NanumGothic-Regular.ttf")))
pdfmetrics.registerFont(TTFont("NanumB", str(FONT_DIR / "NanumGothic-Bold.ttf")))
pdfmetrics.registerFont(TTFont("NanumXB", str(FONT_DIR / "NanumGothic-ExtraBold.ttf")))

NAVY = colors.HexColor("#142038")
GOLD = colors.HexColor("#C7A24A")
GRAY = colors.HexColor("#5A6172")
LIGHT = colors.HexColor("#F4F6F9")

# --------------------------------------------------------------------------- #
# 1주차 콘텐츠 (제목/본문카드/멘트/해시태그/발행시간/노출포인트)
# --------------------------------------------------------------------------- #
WEEK = [
    {
        "day": "DAY 1 · 월요일", "time": "오후 7:30",
        "topic": "통장 쪼개기",
        "title": "월급이 남는 사람들의\n통장 쪼개기 4단계",
        "cards": [
            ("1. 왜 통장을 쪼개나요?", "한 통장에 다 두면 얼마 썼는지 모릅니다. 돈의 흐름이 보여야 새는 돈이 잡혀요."),
            ("2. 월급 통장", "월급이 들어오는 메인 통장. 들어오자마자 아래 3개로 자동이체 시킵니다."),
            ("3. 생활비·고정비 통장", "한 달 쓸 돈만 넣어두고 체크카드 연결. 이 안에서만 쓰면 끝."),
            ("4. 비상금·투자 통장", "비상금은 파킹통장, 투자금은 따로. 섞이면 둘 다 무너집니다."),
            ("실천 팁", "월급날 '자동이체'로 세팅해두면 의지가 필요 없어요."),
        ],
        "caption": "월급은 그대로인데 왜 항상 텅장일까요? 💸\n\n돈 잘 모으는 사람들의 공통점은 '통장 쪼개기'예요. 오늘 4단계만 따라 세팅해보세요. 다음 달 잔고가 달라집니다.\n\n👉 나중에 세팅할 때 보려면 [저장] 필수!\n여러분은 통장 몇 개로 나눠 쓰세요? 댓글로 알려주세요 👇",
        "hashtags": ["#통장쪼개기", "#사회초년생", "#재테크", "#돈관리", "#월급관리",
                     "#짠테크", "#재테크공부", "#저축", "#돈공부", "#직장인",
                     "#사회초년생재테크", "#가계부", "#money", "#절약팁"],
        "hook": "'텅장'이라는 공감 키워드 + 숫자(4단계)로 호기심 자극. 저장 유도형.",
    },
    {
        "day": "DAY 2 · 화요일", "time": "오후 8:00",
        "topic": "비상금",
        "title": "갑자기 닥쳐도\n안 무너지는 비상금 공식",
        "cards": [
            ("1. 비상금이 먼저다", "투자보다, 적금보다 먼저. 비상금이 없으면 위기에 빚을 집니다."),
            ("2. 얼마가 적정?", "생활비 기준 3~6개월치. 사회초년생은 우선 3개월치가 목표."),
            ("3. 어디에 두나요?", "파킹통장·CMA에. 하루만 넣어도 이자 + 즉시 출금 가능."),
            ("4. 모으는 순서", "비상금 채우기 → 그 다음 투자. 순서를 지켜야 흔들리지 않아요."),
            ("5. 손대지 않는 법", "별도 통장 + 체크카드 미연결. '보이지 않게' 두는 게 핵심."),
        ],
        "caption": "병원비, 갑작스런 퇴사, 경조사… 인생은 늘 예고가 없죠 😮‍💨\n\n이때 '비상금'이 있으면 버티고, 없으면 카드빚으로 시작합니다. 사회초년생이라면 투자보다 이걸 먼저 만드세요.\n\n💾 저장해두고 이번 달부터 시작!\n비상금, 지금 얼마나 모아두셨나요? 👇",
        "hashtags": ["#비상금", "#사회초년생", "#재테크", "#돈관리", "#파킹통장",
                     "#짠테크", "#저축", "#재테크공부", "#돈공부", "#월급관리",
                     "#CMA", "#사회초년생재테크", "#money", "#금융꿀팁"],
        "hook": "'예고 없는 위기' 불안 자극 → 해결책 제시. 신뢰형 정보.",
    },
    {
        "day": "DAY 3 · 수요일", "time": "오후 7:30",
        "topic": "고정비 다이어트",
        "title": "매달 새는 돈\n5만원 막는 법",
        "cards": [
            ("1. 고정비가 진짜 적", "한 번 새면 매달 빠져요. 5천원 × 12개월 = 6만원입니다."),
            ("2. 안 쓰는 구독 점검", "OTT·음악·클라우드·앱 결제. 3개월 안 본 건 바로 해지."),
            ("3. 통신비 다이어트", "알뜰폰으로 갈아타면 월 3~4만원 절약. 번호 그대로 가능."),
            ("4. 보험 리모델링", "소득 대비 과한 보험료는 점검. 중복 보장은 정리."),
            ("5. 자동 절약 세팅", "줄인 고정비만큼 저축 통장에 자동이체로 옮기기."),
        ],
        "caption": "돈은 '많이 버는 것'보다 '안 새게 하는 것'이 먼저예요 🔍\n\n오늘은 매달 조용히 빠져나가는 고정비 점검 리스트! 딱 30분이면 연 60만원이 굳습니다.\n\n📌 지금 폰 들고 하나씩 체크해보세요\n가장 아까운 고정비, 뭐였어요? 댓글 👇",
        "hashtags": ["#고정비", "#절약", "#짠테크", "#사회초년생", "#재테크",
                     "#돈관리", "#알뜰폰", "#구독해지", "#생활비절약", "#재테크공부",
                     "#돈공부", "#절약팁", "#money", "#가계부"],
        "hook": "구체적 금액(5만원/60만원)으로 즉시 행동 유도. 실용형.",
    },
    {
        "day": "DAY 4 · 목요일", "time": "오후 8:00",
        "topic": "청년 지원금",
        "title": "놓치면 손해!\n청년 지원금 BEST 5",
        "cards": [
            ("1. 청년도약계좌", "정부 기여금 + 비과세. 5년 만기로 목돈 마련. 소득 요건 확인."),
            ("2. 청년 주택드림 청약", "내 집 마련 첫 단추. 우대금리 + 청약 연계 혜택."),
            ("3. 국민내일배움카드", "자기계발·자격증 비용 지원. 직장인도 신청 가능."),
            ("4. 청년 월세 지원", "조건 충족 시 월세 일부 지원. 지자체별로 추가 혜택."),
            ("5. 지자체 청년 정책", "사는 지역 '청년정책포털' 꼭 확인. 숨은 지원금 많아요."),
        ],
        "caption": "정부가 주는 돈, 몰라서 못 받으면 너무 아깝잖아요 🥲\n\n사회초년생이 챙길 수 있는 청년 지원금만 모았어요. 신청 조건은 매년 바뀌니 꼭 최신 공고 확인하세요!\n\n🔖 저장하고 하나씩 신청하기\n주변에 알려줄 친구 [태그]해주세요 👇\n\n※ 자세한 조건은 각 기관 공고 기준",
        "hashtags": ["#청년지원금", "#청년도약계좌", "#사회초년생", "#재테크", "#돈관리",
                     "#청년정책", "#정부지원금", "#청년청약", "#저축", "#재테크공부",
                     "#내집마련", "#money", "#사회초년생재테크", "#꿀팁"],
        "hook": "'몰라서 손해' FOMO + 친구 태그 유도(공유 확산). 도달 폭발형.",
    },
    {
        "day": "DAY 5 · 금요일", "time": "오후 7:00",
        "topic": "자동 저축",
        "title": "의지박약도 성공하는\n자동 저축 세팅법",
        "cards": [
            ("1. 의지로는 안 모입니다", "'쓰고 남으면 저축'은 100% 실패. 구조를 바꿔야 해요."),
            ("2. 선저축 후지출", "월급날 = 저축날. 받자마자 떼고 남은 걸로 생활."),
            ("3. 자동이체 세팅", "저축·투자 통장으로 자동이체 예약. 손이 갈 틈을 없앤다."),
            ("4. 금액은 소득의 10%부터", "부담되면 10%로 시작, 익숙해지면 늘리기."),
            ("5. 풍차돌리기 적금", "매달 새 적금 1개씩. 다음 달부터 만기 이자가 쏠쏠."),
        ],
        "caption": "저축, 의지로 하려니까 매번 실패하셨죠? 🙃\n\n비결은 '의지'가 아니라 '자동화'예요. 월급날 자동이체 한 번만 걸어두면 통장이 알아서 모읍니다.\n\n💰 불금에 5분 투자해서 세팅 ㄱㄱ\n[저장]하고 오늘 바로 신청해보세요!",
        "hashtags": ["#자동저축", "#선저축", "#적금", "#사회초년생", "#재테크",
                     "#돈관리", "#짠테크", "#저축습관", "#재테크공부", "#월급관리",
                     "#풍차돌리기", "#돈공부", "#money", "#저축"],
        "hook": "'의지박약' 셀프디스 공감 + 즉시 실행 CTA. 저장+행동형.",
    },
    {
        "day": "DAY 6 · 토요일", "time": "오전 11:00",
        "topic": "소액 투자 입문",
        "title": "10만원으로 시작하는\n첫 투자 가이드",
        "cards": [
            ("1. 투자는 빨리 시작이 답", "수익률보다 '시간'이 복리를 만듭니다. 소액이라도 일찍."),
            ("2. 비상금부터 확인", "비상금 없이 투자 X. 잃어도 되는 돈으로만 시작."),
            ("3. 첫 상품은 지수 ETF", "개별 종목보다 시장 전체에. 분산되어 덜 위험해요."),
            ("4. 적립식으로 꾸준히", "매달 같은 금액 자동 매수. 타이밍 고민이 사라집니다."),
            ("5. 절대 하지 말 것", "빚투·몰빵·단타. 초보가 돈 잃는 3대 패턴이에요."),
        ],
        "caption": "투자, 돈 많아야 하는 거 아니에요. 10만원이면 충분합니다 📈\n\n중요한 건 금액이 아니라 '일찍, 꾸준히'예요. 오늘 첫걸음 가이드 정리했어요. (※ 투자는 본인 판단과 책임으로!)\n\n📌 저장하고 천천히 다시 보기\n투자 시작이 망설여지는 이유, 뭐예요? 👇",
        "hashtags": ["#소액투자", "#ETF", "#투자입문", "#사회초년생", "#재테크",
                     "#돈관리", "#재테크공부", "#적립식투자", "#주식초보", "#돈공부",
                     "#경제공부", "#money", "#투자공부", "#재테크초보"],
        "hook": "진입장벽 해소('10만원이면 충분') + 면책 문구로 신뢰. 주말 오전 도달.",
    },
    {
        "day": "DAY 7 · 일요일", "time": "오후 6:00",
        "topic": "신용점수",
        "title": "사회초년생 신용점수\n빠르게 올리는 습관 5",
        "cards": [
            ("1. 신용점수가 왜 중요?", "대출 금리·한도가 달라져요. 사회초년생일수록 미리 관리."),
            ("2. 통신·공과금 자동납부", "연체 0건이 핵심. 자동이체로 깜빡 연체를 막으세요."),
            ("3. 체크카드도 도움", "꾸준한 사용 실적은 신용에 +. 무리한 카드는 금물."),
            ("4. 비금융 정보 등록", "통신·건보료 납부내역 등록하면 점수 상승 가능."),
            ("5. 주기적으로 조회", "무료 조회는 점수에 영향 없어요. 월 1회 체크 습관."),
        ],
        "caption": "신용점수, 필요할 때 올리려면 이미 늦어요 ⏰\n\n사회초년생일 때부터 작은 습관만 들여도 대출·카드에서 유리해집니다. 오늘 5가지만 기억하세요!\n\n🔖 한 주 마무리, 저장하고 천천히 실천\n이번 주 콘텐츠 도움 됐다면 팔로우 부탁해요 🙏",
        "hashtags": ["#신용점수", "#신용관리", "#사회초년생", "#재테크", "#돈관리",
                     "#신용점수올리기", "#재테크공부", "#돈공부", "#금융꿀팁", "#직장인",
                     "#대출", "#money", "#사회초년생재테크", "#경제공부"],
        "hook": "'필요할 땐 늦다' 경고형 + 주간 마무리 팔로우 CTA.",
    },
]


def build():
    out = Path("output/1주차_카드뉴스_기획서.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=14 * mm,
        title="1주차 카드뉴스 기획서",
    )
    styles = _styles()
    story = []

    # ---- 표지 ----
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph("1주차 카드뉴스 콘텐츠 기획서", styles["cover"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("사회초년생 재테크 · @money.note", styles["coversub"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("주제: 첫 월급부터 시작하는 돈 관리 기초 7일", styles["coversub"]))
    story.append(Spacer(1, 10 * mm))
    story.append(_overview_table(styles))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("※ 모든 제목·멘트·해시태그는 저장·공유·댓글 유도(노출 최적화) 기준으로 작성되었습니다.",
                           styles["note"]))
    story.append(PageBreak())

    # ---- 발행 캘린더 ----
    story.append(Paragraph("📅 주간 발행 캘린더", styles["h1"]))
    story.append(Spacer(1, 3 * mm))
    story.append(_calendar_table(styles))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("🔑 해시태그 전략", styles["h1"]))
    story.append(Spacer(1, 2 * mm))
    for line in [
        "• <b>믹스 전략</b>: 대형(#재테크 #사회초년생) + 중형(#짠테크 #재테크공부) + 소형/니치(#통장쪼개기 #청년도약계좌) 태그를 섞어 노출 범위와 상위노출 확률을 동시에 노립니다.",
        "• <b>개수</b>: 게시물당 12~15개. 본문 캡션 끝 또는 첫 댓글에 배치(둘 다 노출 동일).",
        "• <b>고정 태그 5개</b>: #사회초년생 #재테크 #돈관리 #재테크공부 #money — 계정 정체성 누적용.",
        "• <b>회피</b>: 과도하게 인기/금지된 태그, 주제와 무관한 태그는 도달을 오히려 깎습니다.",
    ]:
        story.append(Paragraph(line, styles["body"]))
        story.append(Spacer(1, 1.5 * mm))
    story.append(PageBreak())

    # ---- 일자별 상세 ----
    for i, d in enumerate(WEEK):
        story.append(_day_block(d, styles))
        if i % 2 == 1:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 6 * mm))

    doc.build(story, onFirstPage=_bg, onLaterPages=_footer)
    return out


# --------------------------------------------------------------------------- #
# 레이아웃 헬퍼
# --------------------------------------------------------------------------- #
def _styles():
    ss = StyleSheet1()
    def mk(name, **kw):
        ss.add(ParagraphStyle(name, **kw))
    mk("cover", fontName="NanumXB", fontSize=26, textColor=NAVY, leading=32)
    mk("coversub", fontName="NanumB", fontSize=12, textColor=GRAY, leading=18)
    mk("h1", fontName="NanumXB", fontSize=15, textColor=NAVY, leading=20)
    mk("daytitle", fontName="NanumXB", fontSize=14, textColor=colors.white, leading=18)
    mk("daymeta", fontName="NanumB", fontSize=9, textColor=GOLD, leading=12)
    mk("label", fontName="NanumB", fontSize=9.5, textColor=GOLD, leading=13)
    mk("title", fontName="NanumXB", fontSize=15, textColor=NAVY, leading=20)
    mk("body", fontName="Nanum", fontSize=9.8, textColor=colors.HexColor("#34384A"), leading=15)
    mk("cardline", fontName="Nanum", fontSize=9.3, textColor=colors.HexColor("#3C4254"), leading=14)
    mk("tags", fontName="NanumB", fontSize=9.3, textColor=colors.HexColor("#2E5FB0"), leading=15)
    mk("note", fontName="Nanum", fontSize=8.5, textColor=GRAY, leading=12)
    mk("hook", fontName="Nanum", fontSize=8.8, textColor=GRAY, leading=13)
    mk("cell", fontName="Nanum", fontSize=8.6, textColor=colors.HexColor("#34384A"), leading=12)
    mk("cellb", fontName="NanumB", fontSize=8.6, textColor=NAVY, leading=12)
    mk("cellh", fontName="NanumB", fontSize=8.8, textColor=colors.white, leading=12)
    return ss


def _overview_table(styles):
    data = [
        [Paragraph("니치", styles["cellb"]), Paragraph("사회초년생 재테크 (정보형)", styles["cell"])],
        [Paragraph("계정", styles["cellb"]), Paragraph("@money.note", styles["cell"])],
        [Paragraph("발행 빈도", styles["cellb"]), Paragraph("주 7회 (매일 1세트)", styles["cell"])],
        [Paragraph("카드 구성", styles["cellb"]), Paragraph("표지 + 본문 5장 + 마무리(CTA) = 7장", styles["cell"])],
        [Paragraph("목표", styles["cellb"]), Paragraph("저장률↑ · 팔로우 전환 · 1만 팔로워 빌드업 1주차", styles["cell"])],
    ]
    t = Table(data, colWidths=[28 * mm, 140 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D9DEE8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#D9DEE8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _calendar_table(styles):
    header = [Paragraph(x, styles["cellh"]) for x in ["요일", "주제", "발행 시간", "노출 포인트"]]
    rows = [header]
    for d in WEEK:
        rows.append([
            Paragraph(d["day"].split("·")[1].strip(), styles["cell"]),
            Paragraph(d["topic"], styles["cell"]),
            Paragraph(d["time"], styles["cell"]),
            Paragraph(d["hook"], styles["cell"]),
        ])
    t = Table(rows, colWidths=[20 * mm, 30 * mm, 22 * mm, 96 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "NanumB"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D9DEE8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E3E7EF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _day_block(d, styles):
    # 헤더 바
    head = Table(
        [[Paragraph(d["day"], styles["daytitle"]),
          Paragraph(f"⏰ {d['time']} 발행", styles["daymeta"])]],
        colWidths=[120 * mm, 48 * mm],
    )
    head.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    inner = []
    inner.append(Paragraph("제목 (표지)", styles["label"]))
    inner.append(Paragraph(d["title"].replace("\n", "<br/>"), styles["title"]))
    inner.append(Spacer(1, 3 * mm))

    inner.append(Paragraph("본문 카드", styles["label"]))
    for j, (t, b) in enumerate(d["cards"], 1):
        inner.append(Paragraph(f"<b>{t}</b> — {b}", styles["cardline"]))
    inner.append(Spacer(1, 3 * mm))

    inner.append(Paragraph("멘트 (캡션)", styles["label"]))
    inner.append(Paragraph(d["caption"].replace("\n", "<br/>"), styles["body"]))
    inner.append(Spacer(1, 3 * mm))

    inner.append(Paragraph("해시태그", styles["label"]))
    inner.append(Paragraph("  ".join(d["hashtags"]), styles["tags"]))

    body = Table([[inner]], colWidths=[168 * mm])
    body.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
    ]))
    block = Table([[head], [body]], colWidths=[168 * mm], style=TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return KeepTogether(block)


def _bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(GOLD)
    canvas.rect(0, A4[1] - 8 * mm, A4[0], 8 * mm, fill=1, stroke=0)
    canvas.restoreState()
    _footer(canvas, doc)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Nanum", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(18 * mm, 8 * mm, "1주차 카드뉴스 기획서 · @money.note")
    canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"- {doc.page} -")
    canvas.restoreState()


if __name__ == "__main__":
    path = build()
    print(f"✅ 생성 완료: {path}")
