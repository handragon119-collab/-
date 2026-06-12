"""카드뉴스(캐러셀) 이미지 생성기.

prepared_posts.json의 글 3개(피엔·피엠·모키)를 계정별 브랜드 톤으로
1080x1350 카드 4장씩 만들어 assets/cardnews/<계정>/ 에 저장한다.

- 피엔(@pnent_official): 흰·검 톤
- 피엠(@pm_ent2026): 초록(로고색)
- 모키(@moki_ent): 빨강

실행: python3 tools/make_cardnews.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"
OUT_DIR = ROOT / "assets" / "cardnews"

W, H = 1080, 1350
M = 96  # 바깥 여백


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / f"Pretendard-{name}.otf"), size)


# 계정별 브랜드 톤
BRANDS = {
    "pnent_official": {
        "header": "PN ENTERTAINMENT",
        "bg": "#0D0D0F", "fg": "#FFFFFF", "sub": "#A8A8B0", "accent": "#FFFFFF",
        "bar_on_cover": "#FFFFFF",
    },
    "pm_ent2026": {
        "header": "PM ENTERTAINMENT",
        "bg": "#F3FBF6", "fg": "#0B3D2E", "sub": "#4E7263", "accent": "#16A34A",
        "bar_on_cover": "#16A34A",
    },
    "moki_ent": {
        "header": "MOKI ENTERTAINMENT",
        "bg": "#C8102E", "fg": "#FFFFFF", "sub": "#FFD9DE", "accent": "#FFFFFF",
        "bar_on_cover": "#FFFFFF",
    },
}

# 카드 구성: (큰 글, 작은 글) — 큰 글의 \n은 의도한 줄바꿈
CARDS = {
    "pnent_official": [
        ("라이브 켜는 건\n누구나 해.", "문제는 켜고 나서야."),
        ("시청자 0명인 화면에 대고\n혼자 떠드는 거,\n생각보다 빨리 지치거든.", None),
        ("그 구간,\n혼자 안 버텨도 돼.", "우리는 처음부터 옆에서 같이 가는 팀.\n강남 스튜디오에서."),
        ("궁금하면 DM으로\n‘라이브’", "한 마디면 충분해."),
    ],
    "pm_ent2026": [
        ("끼는 있는데\n보여줄 데가 없다?", "그게 제일 아까워."),
        ("노래든 수다든 게임이든,\n방 안에서만 쓰기엔\n아까운 재능이 많아.", None),
        ("틱톡 라이브가\n그 무대가 될 수 있어.", "근데 혼자 시작하면\n길을 한참 돌아가."),
        ("어떻게 시작하냐고?\nDM에 ‘라이브’", "한 마디만 남겨."),
    ],
    "moki_ent": [
        ("‘나도 할 수 있을 것\n같은데…’", "틱톡 라이브 보다가\n그런 적 있지?"),
        ("근데 그 생각,\n대부분 생각으로 끝나.", None),
        ("보는 거랑 하는 건\n완전 다른 재미야.", "해본 사람들은 알아."),
        ("막막하면\n우리랑 같이 하면 돼.", "DM으로 ‘라이브’라고 보내봐."),
    ],
}

HANDLES = {
    "pnent_official": "@pnent_official",
    "pm_ent2026": "@pm_ent2026",
    "moki_ent": "@moki_ent",
}


def draw_tracked(d: ImageDraw.ImageDraw, xy, text, f, fill, tracking=6):
    """자간(tracking)을 띄워 한 글자씩 그린다 — 브랜드 헤더용."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tracking
    return x


def draw_block(d, x, y, text, f, fill, line_gap=1.32):
    """\n 기준 여러 줄을 그리고 끝 y를 반환."""
    lh = f.size * line_gap
    for line in text.split("\n"):
        d.text((x, y), line, font=f, fill=fill)
        y += lh
    return y


def make_card(brand: dict, big: str, small: str | None, page: int, total: int,
              handle: str, is_cover: bool, is_last: bool) -> Image.Image:
    img = Image.new("RGB", (W, H), brand["bg"])
    d = ImageDraw.Draw(img)

    # 상단: 포인트 바 + 브랜드 헤더
    d.rectangle([M, M, M + 64, M + 10], fill=brand["accent"])
    draw_tracked(d, (M, M + 34), brand["header"], font("Bold", 30), brand["fg"], tracking=8)

    # 상단 오른쪽: 페이지 표시
    pf = font("Bold", 30)
    ptxt = f"{page} / {total}"
    d.text((W - M - d.textlength(ptxt, font=pf), M + 34), ptxt, font=pf, fill=brand["sub"])

    # 본문: 큰 글 + 작은 글 (세로 중앙 배치)
    bigf = font("ExtraBold", 88 if is_cover else 76)
    smallf = font("Regular", 42)
    big_h = len(big.split("\n")) * bigf.size * 1.32
    small_h = (len(small.split("\n")) * smallf.size * 1.5 + 36) if small else 0
    y = (H - big_h - small_h) / 2 - 30
    y = draw_block(d, M, y, big, bigf, brand["fg"])
    if small:
        draw_block(d, M, y + 36, small, smallf, brand["sub"], line_gap=1.5)

    # 하단: 계정 핸들 + 안내
    hf = font("Bold", 32)
    d.text((M, H - M - hf.size), handle, font=hf, fill=brand["sub"])
    tail = "DM 💬" if is_last else "다음 →"
    d.text((W - M - d.textlength(tail, font=hf), H - M - hf.size), tail,
           font=hf, fill=brand["accent"])
    return img


def main() -> None:
    for username, cards in CARDS.items():
        brand = BRANDS[username]
        out = OUT_DIR / username
        out.mkdir(parents=True, exist_ok=True)
        total = len(cards)
        for i, (big, small) in enumerate(cards, 1):
            img = make_card(brand, big, small, i, total, HANDLES[username],
                            is_cover=(i == 1), is_last=(i == total))
            p = out / f"{i:02d}.png"
            img.save(p, optimize=True)
            print("✅", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
