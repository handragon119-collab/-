"""카드뉴스 슬라이드를 PIL로 렌더링한다.

표지 / 본문 카드 / 마무리 카드를 디자인 템플릿에 맞춰 이미지로 생성한다.
글자를 직접 그리므로 AI 이미지 생성기와 달리 한글이 깨지지 않고 디자인이 일관된다.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .config import Config
from .content import CardNews
from .fonts import get_font

# 컬러 테마 (배경/글자/포인트색)
THEMES = {
    "navy": {
        "cover_bg": (20, 28, 50), "cover_fg": (255, 255, 255), "cover_sub": (140, 170, 235),
        "accent": (88, 140, 255),
        "body_bg": (247, 248, 251), "body_title": (22, 28, 45),
        "body_text": (60, 66, 82), "footer": (150, 156, 170),
    },
    "mint": {
        "cover_bg": (16, 64, 58), "cover_fg": (255, 255, 255), "cover_sub": (150, 222, 205),
        "accent": (38, 196, 160),
        "body_bg": (246, 251, 249), "body_title": (18, 48, 44),
        "body_text": (58, 74, 70), "footer": (146, 162, 158),
    },
    "coral": {
        "cover_bg": (54, 26, 36), "cover_fg": (255, 255, 255), "cover_sub": (255, 178, 168),
        "accent": (255, 107, 107),
        "body_bg": (252, 247, 246), "body_title": (46, 26, 28),
        "body_text": (78, 62, 62), "footer": (170, 150, 150),
    },
    "cream": {
        "cover_bg": (33, 33, 33), "cover_fg": (255, 248, 232), "cover_sub": (224, 196, 140),
        "accent": (214, 170, 90),
        "body_bg": (250, 246, 238), "body_title": (33, 30, 24),
        "body_text": (74, 68, 56), "footer": (164, 152, 130),
    },
}


def render_cardnews(content: CardNews, config: Config, base_path: str) -> list[str]:
    """카드뉴스 전체를 렌더링하고 생성된 이미지 경로 목록을 반환한다."""
    theme = THEMES.get(config.card_theme, THEMES["navy"])
    w, h = config.card_dimensions
    total = len(content.cards) + 2  # 표지 + 본문 + 마무리
    paths: list[str] = []
    Path(base_path).parent.mkdir(parents=True, exist_ok=True)

    # 표지
    p = f"{base_path}_01_cover.jpg"
    _render_cover(content, theme, (w, h), config.brand_handle, p)
    paths.append(p)

    # 본문 카드들
    for i, card in enumerate(content.cards, start=1):
        p = f"{base_path}_{i+1:02d}_card.jpg"
        _render_content(card, i, len(content.cards), theme, (w, h), config.brand_handle, p)
        paths.append(p)

    # 마무리
    p = f"{base_path}_{total:02d}_closing.jpg"
    _render_closing(content, theme, (w, h), config.brand_handle, p)
    paths.append(p)
    return paths


# --------------------------------------------------------------------------- #
# 슬라이드별 렌더링
# --------------------------------------------------------------------------- #
def _render_cover(content, theme, size, handle, out):
    w, h = size
    img = Image.new("RGB", size, theme["cover_bg"])
    d = ImageDraw.Draw(img)
    margin = int(w * 0.09)

    # 상단 포인트 바
    d.rounded_rectangle([margin, int(h * 0.16), margin + 90, int(h * 0.16) + 14],
                        radius=7, fill=theme["accent"])

    # 보조 문구
    if content.cover_subtitle:
        sub_font = get_font(int(w * 0.040), "bold")
        d.text((margin, int(h * 0.21)), content.cover_subtitle, font=sub_font,
               fill=theme["cover_sub"])

    # 표지 제목 (큰 글씨, 여러 줄)
    title_font = get_font(int(w * 0.092), "extrabold")
    lines = _wrap_lines(d, content.cover_title, title_font, w - 2 * margin)
    y = int(h * 0.28)
    for line in lines:
        d.text((margin, y), line, font=title_font, fill=theme["cover_fg"])
        y += int(title_font.size * 1.22)

    # 스와이프 안내 + 핸들
    hint_font = get_font(int(w * 0.038), "bold")
    d.text((margin, int(h * 0.86)), "밀어서 보기  →", font=hint_font, fill=theme["accent"])
    _footer(d, size, margin, handle, theme["cover_sub"])
    img.save(out, "JPEG", quality=92)


def _render_content(card, idx, total, theme, size, handle, out):
    w, h = size
    img = Image.new("RGB", size, theme["body_bg"])
    d = ImageDraw.Draw(img)
    margin = int(w * 0.09)

    # 페이지 번호 (우상단)
    num_font = get_font(int(w * 0.034), "bold")
    page = f"{idx:02d} / {total:02d}"
    tw = d.textlength(page, font=num_font)
    d.text((w - margin - tw, int(h * 0.07)), page, font=num_font, fill=theme["footer"])

    # 포인트 바 + 제목
    bar_y = int(h * 0.13)
    d.rounded_rectangle([margin, bar_y, margin + 64, bar_y + 12], radius=6,
                        fill=theme["accent"])
    title_font = get_font(int(w * 0.058), "extrabold")
    title_lines = _wrap_lines(d, card.get("title", ""), title_font, w - 2 * margin)
    y = bar_y + int(h * 0.035)
    for line in title_lines:
        d.text((margin, y), line, font=title_font, fill=theme["body_title"])
        y += int(title_font.size * 1.2)

    # 본문
    y += int(h * 0.02)
    body_font = get_font(int(w * 0.044), "regular")
    for para in card.get("body", "").split("\n"):
        for line in _wrap_lines(d, para, body_font, w - 2 * margin):
            d.text((margin, y), line, font=body_font, fill=theme["body_text"])
            y += int(body_font.size * 1.5)
        y += int(body_font.size * 0.4)

    _footer(d, size, margin, handle, theme["footer"])
    img.save(out, "JPEG", quality=92)


def _render_closing(content, theme, size, handle, out):
    w, h = size
    img = Image.new("RGB", size, theme["cover_bg"])
    d = ImageDraw.Draw(img)
    margin = int(w * 0.09)

    title_font = get_font(int(w * 0.072), "extrabold")
    lines = _wrap_lines(d, content.closing_title or "끝까지 봐주셔서 감사해요", title_font,
                        w - 2 * margin)
    y = int(h * 0.34)
    for line in lines:
        d.text((margin, y), line, font=title_font, fill=theme["cover_fg"])
        y += int(title_font.size * 1.22)

    # CTA 버튼 박스
    cta_font = get_font(int(w * 0.044), "bold")
    cta = content.closing_cta or "저장하고 팔로우 ❤️"
    tw = d.textlength(cta, font=cta_font)
    bx0, by0 = margin, y + int(h * 0.03)
    d.rounded_rectangle([bx0, by0, bx0 + tw + int(w * 0.09), by0 + int(h * 0.075)],
                        radius=int(h * 0.0375), fill=theme["accent"])
    d.text((bx0 + int(w * 0.045), by0 + int(h * 0.022)), cta, font=cta_font,
           fill=theme["cover_bg"])

    _footer(d, size, margin, handle, theme["cover_sub"])
    img.save(out, "JPEG", quality=92)


# --------------------------------------------------------------------------- #
# 유틸
# --------------------------------------------------------------------------- #
def _footer(d, size, margin, handle, color):
    if not handle:
        return
    w, h = size
    font = get_font(int(w * 0.034), "bold")
    d.text((margin, int(h * 0.94)), handle, font=font, fill=color)


def _wrap_lines(d, text, font, max_width):
    """픽셀 폭 기준으로 줄바꿈. 명시적 줄바꿈(\\n)은 보존하고,
    공백이 없는 긴 토큰은 글자 단위로 끊는다."""
    text = (text or "").strip()
    if not text:
        return []
    # 명시적 줄바꿈을 먼저 분리해 각 단락을 개별 래핑
    if "\n" in text:
        out = []
        for seg in text.split("\n"):
            out.extend(_wrap_lines(d, seg, font, max_width))
        return out
    lines, cur = [], ""
    for word in text.split(" "):
        trial = f"{cur} {word}".strip()
        if d.textlength(trial, font=font) <= max_width:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        # 단어 자체가 폭을 넘으면 글자 단위로 분할
        if d.textlength(word, font=font) > max_width:
            piece = ""
            for ch in word:
                if d.textlength(piece + ch, font=font) <= max_width:
                    piece += ch
                else:
                    lines.append(piece)
                    piece = ch
            cur = piece
        else:
            cur = word
    if cur:
        lines.append(cur)
    return lines
