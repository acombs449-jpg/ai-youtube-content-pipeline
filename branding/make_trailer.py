"""One-off: render the Money Minute channel trailer (~30s, 16:9) from a fixed
script. Reuses the normal voice/visuals/render pipeline. Output goes to ./output;
upload it and set it as the channel trailer in YouTube Studio."""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from pipeline import voice, visuals, render

NARRATION = (
    "Nobody ever taught you how money actually works. So let's fix that, one "
    "drop at a time. This is The Daily Drop. Every single day, one quick, "
    "no-nonsense money win you can use right now: how to budget without "
    "spreadsheets, save without feeling broke, fix your credit, and stop letting "
    "your money slip through your fingers. No jargon. No get-rich-quick nonsense. "
    "Just simple money skills, explained fast. Subscribe to The Daily Drop, and "
    "get a little richer every single day. Your first drop starts now."
)
KEYWORDS = [
    "counting cash money", "person budgeting laptop", "credit card payment",
    "saving coins jar", "stock market chart screen", "happy person smartphone",
]


def main():
    f = config.fmt("long")  # 16:9, no burned captions
    slug = datetime.now().strftime("trailer_%Y%m%d_%H%M%S")
    work = config.WORK / slug
    work.mkdir(parents=True, exist_ok=True)

    print("voiceover...")
    audio = work / "narration.mp3"
    voice.synthesize(NARRATION, audio)

    print("B-roll...")
    broll = visuals.fetch_broll(KEYWORDS, work, want=6, orientation="landscape")
    if not broll:
        raise SystemExit("No B-roll downloaded.")

    print("render...")
    out = config.OUTPUT / f"{slug}.mp4"
    render.render(broll, audio, None, out, work, f)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
