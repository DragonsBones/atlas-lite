# core/watermark.py
from __future__ import annotations
import io
from PIL import Image, ImageDraw, ImageFont

def add_png_watermark(png_bytes: bytes, text: str = "Atlas Lite") -> bytes:
    """
    Adds a semi-transparent diagonal tiled watermark to a PNG (bytes).
    Returns new PNG bytes.
    """
    base = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    w, h = base.size

    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Font: try Arial; fallback safely
    try:
        font_size = max(18, int(min(w, h) * 0.06))
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    # Tile the watermark so cropping/snips still show it
    step = max(140, int(min(w, h) * 0.18))
    for y in range(-h, h * 2, step):
        for x in range(-w, w * 2, step):
            draw.text((x, y), text, fill=(0, 0, 0, 22), font=font)

    # Diagonal
    overlay = overlay.rotate(-30, resample=Image.BICUBIC, expand=False)

    out = Image.alpha_composite(base, overlay).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
