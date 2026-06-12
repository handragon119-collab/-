"""카드뉴스 렌더 엔진 — 계정별 브랜드 톤 + 매번 조금씩 다른 디자인 변형.

render_post(username, post_id, cards, seed) 로 카드 세트를 만들어
assets/cardnews/<post_id>/01.png ... 에 저장한다.

브랜드 색(피엔=흑백 / 피엠=초록 / 모키=빨강)은 유지하되, seed에 따라
배경 톤·강조 스타일·레이아웃·글자 크기를 조금씩 바꿔 매번 느낌이 다르다.
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


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / f"Pretendard-{name}.otf"), size)


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % rgb


def _shift(hex_color: str, dl: float = 0.0, ds: float = 0.0) -> str:
    """명도(dl)·채도(ds)를 살짝 조절해 같은 색의 다른 톤을 만든다."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    ll = min(1, max(0, ll + dl))
    ss = min(1, max(0, ss + ds))
    r, g, b = colorsys.hls_to_rgb(hh, ll, ss)
    return _hex((round(r * 255), round(g * 255), round(b * 255)))


# 계정별 '스킴'(서로 가까운 색 조합 여러 개) — 매번 그중 하나가 골라진다.
BRANDS = {
    "pnent_official": {
        "header": "PN ENTERTAINMENT",
        "schemes": [
            {"bg": "#0D0D0F", "fg": "#FFFFFF", "sub": "#9A9AA6", "accent": "#FFFFFF"},
            {"bg": "#101418", "fg": "#FFFFFF", "sub": "#8E97A4", "accent": "#E6E6EE"},
            {"bg": "#0A0C12", "fg": "#F4F5FA", "sub": "#8890A0", "accent": "#C9CBD6"},
            {"bg": "#15120F", "fg": "#FFFFFF", "sub": "#A39B92", "accent": "#F0E9E2"},
        ],
    },
    "pm_ent2026": {
        "header": "PM ENTERTAINMENT",
        "schemes": [
            {"bg": "#F2FBF6", "fg": "#0B3D2E", "sub": "#4E7263", "accent": "#16A34A"},
            {"bg": "#EAF7F0", "fg": "#0C3A2C", "sub": "#52786A", "accent": "#0EA371"},
            {"bg": "#EEF6EC", "fg": "#123D24", "sub": "#5A7B5C", "accent": "#22A55B"},
            {"bg": "#0B3D2E", "fg": "#EAFBF1", "sub": "#8FBFA9", "accent": "#34D399"},
        ],
    },
    "moki_ent": {
        "header": "MOKI ENTERTAINMENT",
        "schemes": [
            {"bg": "#C8102E", "fg": "#FFFFFF", "sub": "#FFD2D9", "accent": "#FFFFFF"},
            {"bg": "#B60D29", "fg": "#FFFFFF", "sub": "#FFC9D2", "accent": "#FFE3E7"},
            {"bg": "#D11233", "fg": "#FFFFFF", "sub": "#FFD7DD", "accent": "#FFFFFF"},
            {"bg": "#1A0608", "fg": "#FFFFFF", "sub": "#E59AA5", "accent": "#FF3B5C"},
        ],
    },
}


def variant(seed: int, username: str) -> dict:
    b = BRANDS[username]
    sc = dict(b["schemes"][seed % len(b["schemes"])])
    # 같은 스킴이라도 배경 명도를 미세하게 흔들어 매번 다르게
    jl = [-0.015, 0.0, 0.02, 0.035][(seed // 4) % 4]
    sc["bg"] = _shift(sc["bg"], dl=jl)
    sc["accent_style"] = ["bar", "underline", "dot"][seed % 3]
    sc["align"] = ["center", "upper"][(seed // 3) % 2]
    sc["quote"] = bool((seed // 2) % 2)
    sc["big_size"] = 80 + [0, 4, -4, 8][seed % 4]
    sc["header"] = b["header"]
    return sc


def _tracked(d, xy, text, f, fill, tracking=8):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tracking
    return x


def _block(d, x, y, text, f, fill, line_gap=1.32):
    lh = f.size * line_gap
    for line in text.split("\n"):
        d.text((x, y), line, font=f, fill=fill)
        y += lh
    return y


def _accent(d, v, y_top):
    style, col = v["accent_style"], v["accent"]
    if style == "bar":
        d.rectangle([M, y_top, M + 64, y_top + 10], fill=col)
    elif style == "underline":
        d.rectangle([M, y_top + 4, M + 120, y_top + 9], fill=col)
    else:  # dot
        d.ellipse([M, y_top - 2, M + 18, y_top + 16], fill=col)


def _card(v, big, small, page, total, handle, is_cover, is_last):
    img = Image.new("RGB", (W, H), v["bg"])
    d = ImageDraw.Draw(img)

    _accent(d, v, M)
    _tracked(d, (M, M + 34), v["header"], font("Bold", 30), v["fg"])
    pf = font("Bold", 30)
    ptxt = f"{page} / {total}"
    d.text((W - M - d.textlength(ptxt, font=pf), M + 34), ptxt, font=pf, fill=v["sub"])

    bigf = font("ExtraBold", v["big_size"] + (8 if is_cover else 0))
    smallf = font("Regular", 42)
    if v["quote"] and is_cover:
        qf = font("ExtraBold", 150)
        d.text((M - 8, M + 78), "“", font=qf, fill=v["accent"])

    big_h = len(big.split("\n")) * bigf.size * 1.32
    small_h = (len(small.split("\n")) * smallf.size * 1.5 + 36) if small else 0
    if v["align"] == "center":
        y = (H - big_h - small_h) / 2 - 20
    else:
        y = M + 230
    y = _block(d, M, y, big, bigf, v["fg"])
    if small:
        _block(d, M, y + 36, small, smallf, v["sub"], line_gap=1.5)

    hf = font("Bold", 32)
    d.text((M, H - M - hf.size), handle, font=hf, fill=v["sub"])
    if not is_last:  # 마지막 장엔 굳이 'DM' 박지 않음 — 공식 계정 톤
        tail = "다음 →"
        d.text((W - M - d.textlength(tail, font=hf), H - M - hf.size), tail,
               font=hf, fill=v["accent"])
    return img


def render_post(username: str, post_id: str, cards: list[tuple], seed: int,
                handle: str) -> list[str]:
    """cards: [(big, small), ...] (보통 4장). 저장 경로(상대) 목록 반환."""
    v = variant(seed, username)
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
