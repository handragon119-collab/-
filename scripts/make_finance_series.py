"""금융 카드뉴스 10편 시리즈 제작 (번호 01~10, luxe 테마).

콘텐츠는 정확성 우선으로 작성하고, 변동 가능한 수치/제도는 공신력 기관 확인을
명시한다(팩트 검증 원칙). 카드 렌더 + 표지 몽타주 + 카피 인덱스 PDF를 생성한다.

실행:  python scripts/make_finance_series.py
출력:  output/finance_series/ , output/finance_10_covers.jpg ,
       output/금융카드뉴스_10편_인덱스.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from instagram_auto import Config  # noqa: E402
from instagram_auto.card_render import render_cardnews  # noqa: E402
from instagram_auto.content import CardNews  # noqa: E402

HANDLE = "@money.note"          # ← 본인 계정으로 변경
KICKER = "금융 가이드"
THEME = "luxe"

# 공통 면책(정확성): 변동 항목은 기관 확인 유도
DISCLAIMER = "※ 제도·한도·세율은 바뀔 수 있어요. 실행 전 해당 기관에서 최신 기준 확인!"

SERIES = [
    CardNews(
        cover_title="예금자보호\n제대로 알기",
        cover_subtitle="은행이 망해도 내 돈 지키는 법",
        cards=[
            ("예금자보호란?", "금융사가 파산해도 예금보험공사(KDIC)가\n예금 원금+이자를 한도 내에서 보장하는 제도."),
            ("한도는 '금융사별'", "1인당, 은행별로 각각 적용돼요.\n한 은행에 몰지 말고 나눠 담는 게 안전."),
            ("보호되는 것 vs 아닌 것", "예·적금은 보호 O.\n펀드·주식·ELS·청약은 보호 대상 X."),
            ("한도 초과라면", "여러 금융사에 분산 예치.\n가족 명의 분산도 방법이에요."),
            ("가입 전 확인", "상품에 '예금자보호' 문구 확인.\n현재 보호한도는 예보 홈페이지에서 체크."),
        ],
        closing_title="원금은\n지키고 시작하기",
        closing_cta="저장하고 팔로우",
        caption="은행도 망할 수 있다는 사실, 알고 계셨나요? 🏦\n\n그래서 있는 게 '예금자보호'예요. 내 돈이 어디까지 보호되는지 정확히 알아야 안전하게 굴립니다.\n\n📌 근거: 예금보험공사(KDIC)·금융감독원\n💾 저장하고 내 통장 점검!\n" + DISCLAIMER,
        hashtags=["#예금자보호", "#예금보험공사", "#재테크", "#돈관리", "#예적금",
                  "#금융상식", "#재테크공부", "#돈공부", "#저축", "#금융꿀팁",
                  "#사회초년생", "#money", "#경제공부", "#안전자산"],
    ),
    CardNews(
        cover_title="연말정산\n환급 늘리는 법",
        cover_subtitle="'13월의 월급' 만드는 공제 핵심",
        cards=[
            ("연말정산이란?", "1년간 낸 세금을 정산해\n더 냈으면 돌려받고, 덜 냈으면 더 내는 절차."),
            ("소득공제 vs 세액공제", "소득공제는 과세표준을↓,\n세액공제는 세금 자체를↓. 둘 다 챙기기."),
            ("연금계좌 세액공제", "연금저축·IRP 납입액은\n세액공제 대상. 노후준비+절세 한 번에."),
            ("신용카드 vs 체크카드", "연봉 25% 초과분부터 공제.\n체크·현금영수증 공제율이 더 높아요."),
            ("놓치기 쉬운 항목", "월세·기부금·의료비·교육비.\n홈택스 '간소화'로 빠짐없이 확인."),
        ],
        closing_title="아는 만큼\n돌려받습니다",
        closing_cta="저장하고 팔로우",
        caption="같은 월급인데 누구는 환급, 누구는 토해내죠 😮\n\n차이는 '공제를 아느냐'예요. 미리 알아야 12월 전에 준비합니다.\n\n📌 근거: 국세청 홈택스\n🔖 저장하고 연말 전에 세팅!\n" + DISCLAIMER,
        hashtags=["#연말정산", "#세액공제", "#소득공제", "#절세", "#재테크",
                  "#돈관리", "#직장인", "#13월의월급", "#연금저축", "#IRP",
                  "#재테크공부", "#money", "#세금", "#홈택스"],
    ),
    CardNews(
        cover_title="신용점수\n올리는 정석",
        cover_subtitle="대출·카드에서 유리해지는 습관",
        cards=[
            ("점수는 누가 매기나?", "KCB·NICE 같은 신용평가사가 산정.\n금융사는 이 점수로 금리·한도를 정해요."),
            ("1순위는 '연체 0'", "단 며칠 연체도 치명적.\n통신·공과금 자동납부로 막으세요."),
            ("카드 사용률 관리", "한도의 30% 이내로 쓰면 유리.\n꾸준한 실적도 +가 됩니다."),
            ("비금융정보 등록", "통신비·건보료 납부내역 등록 시\n점수 상승에 도움될 수 있어요."),
            ("조회는 점수에 무해", "본인 무료조회는 점수 영향 없음.\n월 1회 점검 습관 들이기."),
        ],
        closing_title="신용은\n미리 쌓는 자산",
        closing_cta="저장하고 팔로우",
        caption="신용점수, 필요할 때 올리려면 이미 늦어요 ⏰\n\n평소 습관이 곧 점수입니다. 오늘 5가지만 지켜도 1년 뒤 금리가 달라져요.\n\n📌 근거: 금융감독원·신용평가사(KCB·NICE)\n💾 저장 필수!\n" + DISCLAIMER,
        hashtags=["#신용점수", "#신용관리", "#신용점수올리기", "#재테크", "#돈관리",
                  "#대출", "#금융꿀팁", "#재테크공부", "#돈공부", "#사회초년생",
                  "#신용카드", "#money", "#경제공부", "#금융상식"],
    ),
    CardNews(
        cover_title="ISA 계좌\n절세 활용법",
        cover_subtitle="투자 수익에 붙는 세금 줄이기",
        cards=[
            ("ISA가 뭔가요?", "예금·펀드·주식 등을 한 계좌에 담고\n세제 혜택을 받는 '만능 절세 통장'."),
            ("핵심은 비과세·분리과세", "일정 한도까지 비과세,\n초과분은 낮은 세율로 분리과세돼요."),
            ("3가지 유형", "중개형·신탁형·일임형.\n직접 투자형은 보통 '중개형'을 선택."),
            ("의무가입기간 확인", "최소 보유기간을 채워야\n세제 혜택이 적용됩니다."),
            ("누구에게 유리?", "투자 수익·이자가 있는 사람일수록 ↑.\n납입·세제 한도는 최신 기준 확인."),
        ],
        closing_title="버는 것만큼\n지키는 절세",
        closing_cta="저장하고 팔로우",
        caption="투자로 벌어도 세금으로 새면 아깝잖아요 💸\n\nISA는 그 세금을 합법적으로 줄이는 계좌예요. 한도와 조건만 알면 누구나 활용 가능.\n\n📌 근거: 금융위원회·금융투자협회\n🔖 저장하고 내게 맞는지 체크!\n" + DISCLAIMER,
        hashtags=["#ISA", "#ISA계좌", "#절세", "#재테크", "#돈관리",
                  "#투자", "#비과세", "#재테크공부", "#돈공부", "#주식",
                  "#펀드", "#money", "#세금", "#경제공부"],
    ),
    CardNews(
        cover_title="국민연금\n더 받는 전략",
        cover_subtitle="알고 쓰면 노후 수령액이 달라진다",
        cards=[
            ("수령액의 원리", "가입기간이 길수록, 낸 금액이 클수록↑.\n'얼마나 오래'가 핵심이에요."),
            ("추후납부(추납)", "과거 못 낸 기간을 메우면\n가입기간이 늘어 수령액 증가 가능."),
            ("임의가입 제도", "소득이 없어도 본인이 가입 가능.\n전업주부·학생도 노후 준비 OK."),
            ("연기연금", "수령을 미루면 연 단위로 가산.\n여유가 있다면 고려해볼 옵션."),
            ("내 예상연금 조회", "국민연금공단·앱에서\n예상 수령액을 미리 확인하세요."),
        ],
        closing_title="노후는\n준비한 만큼",
        closing_cta="저장하고 팔로우",
        caption="국민연금, 그냥 떼이는 돈이라 생각하셨나요? 👵👴\n\n제도를 알면 '더 받는' 방법이 생겨요. 미리 설계할수록 노후가 든든해집니다.\n\n📌 근거: 국민연금공단\n💾 저장하고 예상연금 조회 ㄱㄱ\n" + DISCLAIMER,
        hashtags=["#국민연금", "#노후준비", "#연금", "#재테크", "#돈관리",
                  "#추납", "#임의가입", "#연기연금", "#재테크공부", "#돈공부",
                  "#노후", "#money", "#경제공부", "#금융꿀팁"],
    ),
    CardNews(
        cover_title="비상금\n굴리는 법",
        cover_subtitle="묵히지 말고 이자까지 챙기기",
        cards=[
            ("비상금의 조건", "①즉시 출금 ②원금 안전.\n수익률보다 '안전+유동성'이 우선."),
            ("파킹통장", "하루만 넣어도 이자.\n수시 입출금되는 고금리 통장이에요."),
            ("CMA", "증권사 계좌로 하루 단위 수익.\n상품 유형별 보호 여부는 확인 필요."),
            ("얼마나?", "생활비 3~6개월치가 기본.\n사회초년생은 우선 3개월치 목표."),
            ("투자와 분리", "비상금은 투자금과 섞지 않기.\n섞이면 위기에 둘 다 흔들려요."),
        ],
        closing_title="안전하게,\n그러나 놀지 않게",
        closing_cta="저장하고 팔로우",
        caption="비상금을 그냥 보통예금에 두고 계신가요? 😴\n\n같은 돈도 '어디 두느냐'로 이자가 달라져요. 안전하면서 이자까지 챙기는 법!\n\n📌 근거: 금융감독원\n💾 저장하고 통장 갈아타기!\n" + DISCLAIMER,
        hashtags=["#비상금", "#파킹통장", "#CMA", "#재테크", "#돈관리",
                  "#짠테크", "#저축", "#재테크공부", "#돈공부", "#사회초년생",
                  "#금융꿀팁", "#money", "#경제공부", "#통장"],
    ),
    CardNews(
        cover_title="복리의 마법\n72의 법칙",
        cover_subtitle="시간이 돈을 불리는 원리",
        cards=[
            ("복리란?", "이자에 또 이자가 붙는 것.\n시간이 길수록 눈덩이처럼 커져요."),
            ("72의 법칙", "72 ÷ 수익률(%) = 원금 2배 되는 햇수.\n예: 6%면 약 12년."),
            ("빨리 시작이 답", "금액보다 '기간'이 핵심.\n10년 일찍 시작 = 큰 차이."),
            ("적립식의 힘", "매달 꾸준히 = 평균 단가 분산.\n타이밍 스트레스가 줄어요."),
            ("복리의 적: 수수료·세금", "비용이 복리를 갉아먹어요.\n저비용·절세 계좌를 활용."),
        ],
        closing_title="시간을\n내 편으로",
        closing_cta="저장하고 팔로우",
        caption="투자에서 가장 강력한 무기는 '시간'이에요 ⏳\n\n복리와 72의 법칙만 이해해도 왜 일찍 시작해야 하는지 보입니다.\n\n📌 개념 근거: 금융교육 표준(금융감독원 e-금융교육센터)\n💾 저장하고 천천히 곱씹기!\n" + DISCLAIMER,
        hashtags=["#복리", "#72의법칙", "#적립식투자", "#재테크", "#돈관리",
                  "#투자", "#재테크공부", "#돈공부", "#경제공부", "#투자입문",
                  "#장기투자", "#money", "#주식초보", "#금융상식"],
    ),
    CardNews(
        cover_title="보험\n리모델링",
        cover_subtitle="새는 보험료 줄이는 점검법",
        cards=[
            ("왜 점검?", "모르고 가입한 중복·과한 보장이\n매달 돈을 새게 합니다."),
            ("보장 내용부터", "내가 든 보험이 무엇을 보장하는지\n증권으로 먼저 파악하세요."),
            ("중복 보장 정리", "같은 위험을 여러 보험이 보장 중이면\n중복분은 조정 검토."),
            ("소득 대비 보험료", "통상 소득의 일정 비율 이내 권장.\n과하면 생활·저축을 압박해요."),
            ("해지는 신중히", "해지 전 보장 공백·손해 확인.\n전문가·금감원 상담 활용."),
        ],
        closing_title="보장은 알차게\n비용은 가볍게",
        closing_cta="저장하고 팔로우",
        caption="매달 나가는 보험료, 제대로 알고 내고 계신가요? 🧾\n\n점검만 해도 불필요한 지출이 줄어요. 단, 해지는 꼭 신중하게!\n\n📌 근거·상담: 금융감독원·생명/손해보험협회\n💾 저장하고 내 증권 점검!\n" + DISCLAIMER,
        hashtags=["#보험", "#보험리모델링", "#보험료", "#재테크", "#돈관리",
                  "#절약", "#보험점검", "#재테크공부", "#돈공부", "#금융꿀팁",
                  "#가계부", "#money", "#경제공부", "#생활비절약"],
    ),
    CardNews(
        cover_title="대출 갈아타기\n(대환) 체크",
        cover_subtitle="이자 아끼기 전, 꼭 확인할 것",
        cards=[
            ("대환대출이란?", "더 낮은 금리의 대출로 갈아타\n이자 부담을 줄이는 것."),
            ("금리만 보지 말기", "중도상환수수료·한도·기간을\n함께 따져야 진짜 이득."),
            ("총비용으로 비교", "겉금리 말고 실제 부담(수수료 포함)을\n합산해 비교하세요."),
            ("신용점수 영향", "여러 곳 동시 조회보다\n비교 플랫폼의 '조회'를 활용."),
            ("정책·서민 상품 확인", "조건 맞으면 정책서민금융 등\n더 유리한 상품이 있을 수 있어요."),
        ],
        closing_title="같은 빚도\n이자는 다르게",
        closing_cta="저장하고 팔로우",
        caption="대출 이자, 갈아타기만 해도 줄일 수 있어요 🔁\n\n단, 금리만 보고 움직이면 손해 볼 수 있습니다. 총비용으로 비교하세요.\n\n📌 근거: 금융감독원·서민금융진흥원\n💾 저장하고 내 대출 비교!\n" + DISCLAIMER,
        hashtags=["#대환대출", "#대출", "#대출갈아타기", "#재테크", "#돈관리",
                  "#이자", "#금리", "#재테크공부", "#돈공부", "#금융꿀팁",
                  "#서민금융", "#money", "#경제공부", "#생활금융"],
    ),
    CardNews(
        cover_title="주택청약통장\n활용법",
        cover_subtitle="내 집 마련의 첫 단추",
        cards=[
            ("청약통장이란?", "아파트 청약 자격을 위한 통장.\n내 집 마련의 기본 준비물이에요."),
            ("일찍 만들수록 유리", "가입기간·납입횟수가 점수에 반영.\n어릴 때 만들수록 유리합니다."),
            ("매달 꾸준히 납입", "인정되는 납입에는 기준이 있어요.\n연체 없이 꾸준함이 중요."),
            ("청년 우대형 확인", "조건 맞으면 우대금리·비과세 등\n청년 전용 혜택을 챙기세요."),
            ("내 점수 관리", "가점 항목(기간·부양·무주택)을\n미리 이해하고 전략적으로."),
        ],
        closing_title="집은\n준비한 사람 몫",
        closing_cta="저장하고 팔로우",
        caption="내 집 마련, 청약통장부터 시작이에요 🏠\n\n언제 만들고 어떻게 납입하느냐가 미래의 당첨 확률을 바꿉니다.\n\n📌 근거: 국토교통부·금융결제원(청약Home)\n💾 저장하고 오늘 가입 체크!\n" + DISCLAIMER,
        hashtags=["#주택청약", "#청약통장", "#내집마련", "#재테크", "#돈관리",
                  "#청약", "#청년우대형", "#재테크공부", "#돈공부", "#사회초년생",
                  "#부동산", "#money", "#경제공부", "#주거"],
    ),
]


def _cn(raw: CardNews) -> CardNews:
    """cards 튜플 → dict 변환."""
    raw.cards = [{"title": t, "body": b} for (t, b) in raw.cards]
    return raw


def build_montage(cover_paths, out):
    cols, rows = 5, 2
    cw, ch, pad = 300, 375, 18
    W = cols * cw + (cols + 1) * pad
    H = rows * ch + (rows + 1) * pad
    canvas = Image.new("RGB", (W, H), (32, 30, 28))
    for i, p in enumerate(cover_paths):
        im = Image.open(p).resize((cw, ch))
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = pad + r * (ch + pad)
        canvas.paste(im, (x, y))
    canvas.save(out, "JPEG", quality=90)


def build_index_pdf(out):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, StyleSheet1
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)

    fd = Path.home() / ".cache" / "instagram_auto" / "fonts"
    for n, f in [("Nanum", "NanumGothic-Regular.ttf"), ("NanumB", "NanumGothic-Bold.ttf"),
                 ("NanumXB", "NanumGothic-ExtraBold.ttf")]:
        try:
            pdfmetrics.registerFont(TTFont(n, str(fd / f)))
        except Exception:
            pass
    NAVY, GOLD, GRAY = colors.HexColor("#1A1612"), colors.HexColor("#C7A24A"), colors.HexColor("#6E7488")
    ss = StyleSheet1()
    ss.add(ParagraphStyle("t", fontName="NanumXB", fontSize=22, textColor=NAVY, leading=28))
    ss.add(ParagraphStyle("sub", fontName="NanumB", fontSize=11, textColor=GRAY, leading=16))
    ss.add(ParagraphStyle("no", fontName="NanumXB", fontSize=13, textColor=colors.white, leading=16))
    ss.add(ParagraphStyle("ti", fontName="NanumXB", fontSize=13, textColor=NAVY, leading=17))
    ss.add(ParagraphStyle("lbl", fontName="NanumB", fontSize=8.5, textColor=GOLD, leading=12))
    ss.add(ParagraphStyle("bd", fontName="Nanum", fontSize=9, textColor=colors.HexColor("#34302A"), leading=14))
    ss.add(ParagraphStyle("tag", fontName="NanumB", fontSize=8.6, textColor=colors.HexColor("#2E5FB0"), leading=13))

    story = [Spacer(1, 6 * mm), Paragraph("금융 카드뉴스 10편 · 카피 인덱스", ss["t"]),
             Paragraph(f"{KICKER} 시리즈 · {HANDLE} · 제목 · 멘트 · 해시태그", ss["sub"]),
             Spacer(1, 6 * mm)]
    for i, cn in enumerate(SERIES, 1):
        head = Table([[Paragraph(f"NO.{i:02d}", ss["no"]),
                       Paragraph(cn.cover_title.replace("\n", " ") + "  —  " + cn.cover_subtitle, ss["ti"])]],
                     colWidths=[20 * mm, 154 * mm])
        head.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), NAVY),
                                  ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F3EFE7")),
                                  ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                  ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
        inner = [Paragraph("멘트", ss["lbl"]),
                 Paragraph(cn.caption.replace("\n", "<br/>"), ss["bd"]), Spacer(1, 2 * mm),
                 Paragraph("해시태그", ss["lbl"]), Paragraph("  ".join(cn.hashtags), ss["tag"])]
        body = Table([[inner]], colWidths=[174 * mm])
        body.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, GOLD),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                                  ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
        story.append(KeepTogether([head, body, Spacer(1, 5 * mm)]))
    SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=14 * mm, bottomMargin=14 * mm).build(story)


def main():
    cfg = Config()
    cfg.card_theme = THEME
    cfg.brand_handle = HANDLE
    cfg.card_size = "1080x1350"
    out_dir = Path("output/finance_series")
    out_dir.mkdir(parents=True, exist_ok=True)

    cover_paths = []
    for i, raw in enumerate(SERIES, 1):
        cn = _cn(raw)
        base = out_dir / f"{i:02d}_{cn.cover_title.splitlines()[0]}"
        paths = render_cardnews(cn, cfg, str(base), number=i, kicker=KICKER)
        cover_paths.append(paths[0])
        print(f"  ✓ NO.{i:02d}  {cn.cover_title.replace(chr(10),' ')}  ({len(paths)}장)")

    build_montage(cover_paths, "output/finance_10_covers.jpg")
    build_index_pdf("output/금융카드뉴스_10편_인덱스.pdf")
    print("\n✅ 완료: output/finance_series/ , finance_10_covers.jpg , 금융카드뉴스_10편_인덱스.pdf")


if __name__ == "__main__":
    main()
