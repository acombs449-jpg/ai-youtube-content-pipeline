"""Generate a bold, high-CTR 1280x720 thumbnail from a short text phrase.
Big readable text + brand colors + an accent bar. Faceless-friendly."""
import textwrap
from PIL import Image, ImageDraw, ImageFont
import config

BG = "#0F0F14"
YELLOW = "#FFE94D"
CYAN = "#22D3EE"
WHITE = "#FFFFFF"
BOLD = "C:/Windows/Fonts/arialbd.ttf"

W, H = 1280, 720
SS = 2  # supersample


def _fit_font(draw, text, max_w, start):
    size = start
    while size > 60:
        f = ImageFont.truetype(BOLD, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 6
    return ImageFont.truetype(BOLD, 60)


def make(thumb_text: str, out_path):
    text = (thumb_text or config.CHANNEL_NAME).upper().strip()
    img = Image.new("RGB", (W * SS, H * SS), BG)
    d = ImageDraw.Draw(img)

    # left accent bar + bottom brand strip
    d.rectangle([0, 0, 28 * SS, H * SS], fill=YELLOW)
    d.rectangle([0, (H - 70) * SS, W * SS, H * SS], fill=CYAN)

    margin = 110 * SS
    max_w = W * SS - margin * 2
    # wrap into up to 3 lines, sized to fit
    words = text.split()
    lines, line = [], ""
    base = _fit_font(d, max(words, key=len), max_w, 240 * SS)
    for w in words:
        test = (line + " " + w).strip()
        if d.textlength(test, font=base) <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)

    line_h = base.size * 1.12
    total_h = line_h * len(lines)
    y = (H * SS - 70 * SS) / 2 - total_h / 2
    for ln in lines:
        # highlight a "?" or "$" line in yellow, else white
        color = YELLOW if ("?" in ln or "$" in ln) else WHITE
        x = margin
        d.text((x, y), ln, font=base, fill=color)
        y += line_h

    # brand tag bottom-left on the cyan strip
    tag_f = ImageFont.truetype(BOLD, 34 * SS)
    d.text((40 * SS, (H - 56) * SS), config.CHANNEL_NAME.upper(),
           font=tag_f, fill=BG)

    img.resize((W, H), Image.LANCZOS).save(out_path)
    return out_path
