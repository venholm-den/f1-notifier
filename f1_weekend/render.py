from __future__ import annotations

import io
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Pillow is required for graphics. Add 'Pillow' to requirements.txt"
    ) from e


def _font(size: int):
    # DejaVuSans is commonly available on ubuntu runners; fallback to default.
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def render_weekend_card(title: str, lines: list[str], footer: str) -> bytes:
    width = 900
    pad = 32
    bg = (14, 17, 22)
    fg = (235, 240, 246)
    accent = (255, 60, 60)

    font_title = _font(40)
    font_body = _font(22)
    font_small = _font(16)

    # rough height
    height = pad * 2 + 60 + (len(lines) * 30) + 50
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, width, 8], fill=accent)

    y = pad
    draw.text((pad, y), title, font=font_title, fill=fg)
    y += 60

    for line in lines:
        draw.text((pad, y), line, font=font_body, fill=fg)
        y += 30

    draw.text((pad, height - pad - 18), footer, font=font_small, fill=(170, 180, 192))

    bio = io.BytesIO()
    img.save(bio, format="PNG", optimize=True)
    return bio.getvalue()
