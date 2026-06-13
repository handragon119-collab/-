"""카드뉴스 렌더 엔진 — 다양한 색 + 레이아웃 변형.

render_post(username, post_id, cards, color_seed, layout_seed, handle) 로
카드 세트를 만들어 assets/cardnews/<post_id>/01.png ... 에 저장한다.

- 색: 계정 한 톤에 묶지 않고, 12색 팔레트에서 글마다 다른 색(그라데이션) 사용.
- 레이아웃: 6가지 구성(사이드바/색블록/큰 숫자/원형/따옴표/기본)을 돌려가며 적용해
  '글자만 있는 종이' 느낌을 피한다.
"""

from __future__ import annotations

import colorsys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"
OUT_ROOT = ROOT / "assets" / "cardnews"

W, H = 1080, 1350
M = 96

HEADERS = {
    "pnent_official": "PN ENTERTAINMENT",
    "pm_ent2026": "PM ENTERTAINMENT",
    "moki_ent": "MOKI ENTERTAINMENT",
}

# 12색 다양한 팔레트(전 계정 공용). 모두 어두운 배경 + 흰 글자라 가독성 안정적.
PALETTE = [
    {"bg": "#C8102E", "bg2": "#E8434E", "accent": "#FFE08A"},  # red
    {"bg": "#FF7A18", "bg2": "#FF3D6E", "accent": "#FFFFFF"},  # orange→pink
    {"bg": "#D6336C", "bg2": "#A61E4D", "accent": "#FFE08A"},  # magenta
    {"bg": "#6A1B4D", "bg2": "#B5179E", "accent": "#FF8FB0"},  # purple
    {"bg": "#1B1A3A", "bg2": "#2A2960", "accent": "#FF7AA2"},  # indigo
    {"bg": "#16233A", "bg2": "#2E4A78", "accent": "#38BDF8"},  # blue
    {"bg": "#0B3D5C", "bg2": "#1B6E8A", "accent": "#7CF6E0"},  # ocean
    {"bg": "#0E2E2B", "bg2": "#19534B", "accent": "#4ADE80"},  # teal
    {"bg": "#0F5132", "bg2": "#1B8A57", "accent": "#86F7B0"},  # emerald
    {"bg": "#2B2D72", "bg2": "#5B2A86", "accent": "#FFD86F"},  # violet-blue
    {"bg": "#4A0E1A", "bg2": "#9E1B3C", "accent": "#FF6FA3"},  # dark crimson
    {"bg": "#5A2E0A", "bg2": "#B5651D", "accent": "#FFD86F"},  # amber/brown
]

N_LAYOUTS = 6


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / f"Pretendard-{name}.otf"), size)


def _rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(max(0, min(255, c))) for c in rgb)


def _mix(c1: str, c2: str, t: float) -> str:
    a, b = _rgb(c1), _rgb(c2)
    return _hex(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


def _shift(hex_color: str, dl: float = 0.0) -> str:
    r, g, b = (c / 255 for c in _rgb(hex_color))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    ll = min(1, max(0, ll + dl))
    r, g, b = colorsys.hls_to_rgb(hh, ll, ss)
    return _hex((r * 255, g * 255, b * 255))


def _contrast(hex_color: str) -> str:
    r, g, b = _rgb(hex_color)
    return "#15151A" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#FFFFFF"


def variant(color_seed: int, layout_seed: int, username: str) -> dict:
    p = PALETTE[color_seed % len(PALETTE)]
    jl = [-0.01, 0.0, 0.02, 0.035][(color_seed // len(PALETTE)) % 4]
    bg, bg2 = _shift(p["bg"], jl), _shift(p["bg2"], jl)
    fg = "#FFFFFF"
    return {
        "bg": bg, "bg2": bg2, "fg": fg, "sub": _mix(fg, bg, 0.42),
        "accent": p["accent"], "ink": _contrast(p["accent"]),
        "layout": layout_seed % N_LAYOUTS,
        "accent_style": ["bar", "underline", "dot"][layout_seed % 3],
        "align": ["center", "upper"][(layout_seed // 2) % 2],
        "big_size": 78 + [0, 6, -4, 10][color_seed % 4],
        "header": HEADERS.get(username, username.upper()),
    }


def _gradient_bg(c1: str, c2: str) -> Image.Image:
    r1, g1, b1 = _rgb(c1)
    r2, g2, b2 = _rgb(c2)
    col = Image.new("RGB", (1, H))
    px = col.load()
    for y in range(H):
        t = y / (H - 1)
        px[0, y] = (round(r1 + (r2 - r1) * t),
                    round(g1 + (g2 - g1) * t),
                    round(b1 + (b2 - b1) * t))
    return col.resize((W, H))


def _block(d, x, y, text, f, fill, line_gap=1.30):
    lh = f.size * line_gap
    for line in text.split("\n"):
        d.text((x, y), line, font=f, fill=fill)
        y += lh
    return y


def _accent_mark(d, style, accent, x, y_top):
    if style == "bar":
        d.rectangle([x, y_top, x + 64, y_top + 10], fill=accent)
    elif style == "underline":
        d.rectangle([x, y_top + 4, x + 120, y_top + 9], fill=accent)
    else:
        d.ellipse([x, y_top - 2, x + 18, y_top + 16], fill=accent)


def _card(v, big, small, page, total, handle, is_cover, is_last):
    img = _gradient_bg(v["bg"], v["bg2"]).convert("RGBA")
    fg, sub, accent = v["fg"], v["sub"], v["accent"]
    ar = _rgb(accent)
    layout = v["layout"]
    title_x = M
    top_pad = 0

    # ── 레이아웃별 장식(반투명 도형은 별도 레이어에) ──
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(over)
    if layout == 2:      # 상단 색블록 패널
        od.rectangle([0, 0, W, int(H * 0.32)], fill=(*ar, 42))
        top_pad = int(H * 0.32)
    elif layout == 3:    # 거대한 페이지 숫자(고스트)
        od.text((W - 430, H - 600), str(page), font=font("ExtraBold", 520),
                fill=(*ar, 30))
    elif layout == 4:    # 코너 원형
        od.ellipse([W - 300, -300, W + 240, 240], fill=(*ar, 38))
        od.ellipse([W - 150, 120, W - 40, 230], fill=(*ar, 70))
    elif layout == 5:    # 큰 따옴표
        od.text((M - 14, M + 54), "“", font=font("ExtraBold", 320),
                fill=(*ar, 60))
    img = Image.alpha_composite(img, over)
    d = ImageDraw.Draw(img)

    if layout == 1:      # 좌측 컬러 스트라이프
        d.rectangle([0, 0, 20, H], fill=accent)
        title_x = M + 10

    # ── 헤더 + 페이지 ──
    if layout != 1:
        _accent_mark(d, v["accent_style"], accent, M, M)
    hx = title_x if layout == 1 else M
    hf = font("Bold", 30)
    x = hx
    for ch in v["header"]:
        d.text((x, M + 34), ch, font=hf, fill=fg)
        x += d.textlength(ch, font=hf) + 8
    ptxt = f"{page} / {total}"
    d.text((W - M - d.textlength(ptxt, font=hf), M + 34), ptxt, font=hf, fill=sub)

    # ── 본문(큰 글 + 작은 글) ──
    bigf = font("ExtraBold", v["big_size"] + (8 if is_cover else 0))
    smallf = font("Regular", 42)
    big_h = len(big.split("\n")) * bigf.size * 1.30
    small_h = (len(small.split("\n")) * smallf.size * 1.5 + 36) if small else 0
    if top_pad:
        y = top_pad + 70
    elif v["align"] == "upper":
        y = M + 230
    else:
        y = (H - big_h - small_h) / 2 - 10
    y = _block(d, title_x, y, big, bigf, fg)
    if small:
        _block(d, title_x, y + 36, small, smallf, sub, line_gap=1.5)

    # ── 하단: 핸들 + 다음 ──
    ff = font("Bold", 32)
    d.text((title_x, H - M - ff.size), handle, font=ff, fill=sub)
    if not is_last:
        d.text((W - M - d.textlength("다음 →", font=ff), H - M - ff.size),
               "다음 →", font=ff, fill=accent)
    return img.convert("RGB")


def render_post(username: str, post_id: str, cards: list[tuple],
                color_seed: int, layout_seed: int, handle: str) -> list[str]:
    """cards: [(big, small), ...]. 저장 경로(상대) 목록 반환."""
    v = variant(color_seed, layout_seed, username)
    out = OUT_ROOT / post_id
    out.mkdir(parents=True, exist_ok=True)
    total = len(cards)
    paths = []
    for i, (big, small) in enumerate(cards, 1):
        img = _card(v, big, small, i, total, handle,
                    is_cover=(i == 1), is_last=(i == total))
        p = out / f"{i:02d}.png"
        img.save(p, optimize=True)
        paths.append(str(p.relative_to(ROOT)))
    return paths
