"""Generate Money Minute channel art: a profile avatar and a YouTube banner.
Banner keeps all text inside YouTube's 1546x423 'safe area' so it shows on
every device. Renders at 2x then downscales for clean edges."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).parent
BG = "#0F0F14"
YELLOW = "#FFE94D"
CYAN = "#22D3EE"
WHITE = "#FFFFFF"
BOLD = "C:/Windows/Fonts/arialbd.ttf"


def avatar():
    SS = 4
    S = 1080 * SS
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img)
    inset = 70 * SS
    d.ellipse([inset, inset, S - inset, S - inset], outline=CYAN, width=28 * SS)
    f = ImageFont.truetype(BOLD, 620 * SS)
    d.text((S / 2, S / 2 - 30 * SS), "$", font=f, fill=YELLOW, anchor="mm")
    img.resize((1080, 1080), Image.LANCZOS).save(OUT / "yt_avatar.png")


def _fit_font(draw, text, max_w, start, floor=48):
    """Shrink font size until `text` fits max_w, so a longer headline/tagline
    from the identity-refresh workflow can't silently overflow the banner."""
    size = start
    while size > floor:
        f = ImageFont.truetype(BOLD, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 6
    return ImageFont.truetype(BOLD, floor)


def banner(headline="THE DAILY DROP", tagline="daily money tips, explained fast"):
    SS = 2
    W, H = 2560 * SS, 1440 * SS
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    cx, cy = W / 2, H / 2
    safe_w = 1546 * SS  # YouTube's banner "safe area" that shows on every device
    # subtle accent bars outside the safe area
    d.rectangle([0, 0, W, 12 * SS], fill=YELLOW)
    d.rectangle([0, H - 12 * SS, W, H], fill=CYAN)
    # channel name + tagline, centered inside safe area, auto-fit to width
    name_f = _fit_font(d, headline.upper(), safe_w, 190 * SS)
    tag_f = _fit_font(d, tagline, safe_w, 70 * SS, floor=40)
    d.text((cx, cy - 70 * SS), headline.upper(), font=name_f, fill=YELLOW, anchor="mm")
    d.text((cx, cy + 105 * SS), tagline, font=tag_f, fill=WHITE, anchor="mm")
    img.resize((2560, 1440), Image.LANCZOS).save(OUT / "yt_banner.png")


if __name__ == "__main__":
    import shutil
    # Reuse the TikTok "The Daily Drop" bolt avatar for a unified cross-platform brand.
    bolt = Path.home() / "tiktok-agent" / "branding" / "avatar_FINAL.png"
    if bolt.exists():
        shutil.copy(bolt, OUT / "yt_avatar.png")
    else:
        avatar()  # fallback to the $ mark
    banner()
    print(OUT / "yt_avatar.png")
    print(OUT / "yt_banner.png")
