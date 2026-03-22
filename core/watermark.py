# core/watermark.py
from __future__ import annotations
import io
from PIL import Image, ImageDraw, ImageFont


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def add_png_watermark(
    png_bytes: bytes,
    text: str = "Atlas",
    bg_color: str = "#F4EFE6",
    brand_mark_color: str = "",
) -> bytes:
    """
    Stamps an embossed text watermark in the bottom-right corner of the chart
    canvas. The effect uses a light highlight offset and a dark shadow offset
    on a background-toned fill so the mark reads as pressed/raised rather than
    as an obtrusive label. Falls back gracefully if font loading fails.

    If brand_mark_color is set, a thin coloured stripe is drawn at the very
    top of the canvas — the editorial identity mark used by the Cicero theme.
    """
    base = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    w, h = base.size

    # Brand mark stripe — drawn directly on base before watermark overlay.
    # Target: 3px visual at any export scale (scale=2 → 6px, scale=3 → 9px).
    if brand_mark_color:
        brand_rgb = _hex_to_rgb(brand_mark_color)
        brand_draw = ImageDraw.Draw(base)
        stripe_h = max(4, round(h / 100))  # ≈3px visual at 2× and 3× export scales
        brand_draw.rectangle([0, 0, w - 1, stripe_h - 1], fill=brand_rgb + (255,))

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Font — scale with image so it stays proportional at any export scale
    font_size = max(13, int(min(w, h) * 0.015))
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    margin_x = max(18, w // 36)
    margin_y = max(14, h // 36)
    x = w - tw - margin_x
    y = h - th - margin_y

    # Derive emboss colours from the chart background
    bg = _hex_to_rgb(bg_color)
    # Highlight: blend bg toward white (~40% lighter)
    highlight = tuple(min(255, int(c + (255 - c) * 0.55)) for c in bg) + (130,)
    # Shadow: darken bg (~28%)
    shadow = tuple(max(0, int(c * 0.72)) for c in bg) + (110,)
    # Fill: bg colour at low opacity — "invisible ink" that completes the stamp
    fill = bg + (38,)

    # Raised emboss: highlight top-left, shadow bottom-right
    draw.text((x - 1, y - 1), text, font=font, fill=highlight)
    draw.text((x + 1, y + 1), text, font=font, fill=shadow)
    draw.text((x,     y    ), text, font=font, fill=fill)

    out = Image.alpha_composite(base, overlay).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
