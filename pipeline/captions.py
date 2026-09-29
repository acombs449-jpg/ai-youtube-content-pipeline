"""Build subtitle files from word timestamps.
.ass (burned-in, punchy 3-word bursts) is used for Shorts.
.srt (uploaded as a real caption track via the API) is used for every format —
this replaces reliance on YouTube's own auto-captions, which are speech-to-text
guesses and can mis-transcribe names/terms (a real risk for Case Files)."""

_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop, Arial Black, 96, &H00FFFFFF, &H00000000, &H80000000, -1, 1, 6, 3, 5, 80, 80, 0, 1

[Events]
Format: Layer, Start, End, Style, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(sec: float) -> str:
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(words: list[dict], out_path, per_group: int = 3):
    lines = [_HEADER]
    for i in range(0, len(words), per_group):
        g = words[i:i + per_group]
        text = " ".join(w["word"] for w in g).upper().replace("\n", " ")
        lines.append(f"Dialogue: 0,{_ts(g[0]['start'])},{_ts(g[-1]['end'])},Pop,,0,0,0,,{text}")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _srt_ts(sec: float) -> str:
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = sec % 60
    whole = int(s)
    ms = round((s - whole) * 1000)
    if ms == 1000:  # rounding carry
        ms = 0
        whole += 1
    return f"{h:02d}:{m:02d}:{whole:02d},{ms:03d}"


def build_srt(words: list[dict], out_path, max_words: int = 9, max_seconds: float = 4.0):
    """Group into natural reading-length cues (real captions, not burst-style)."""
    if not words:
        out_path.write_text("", encoding="utf-8")
        return out_path
    cues, cur, idx = [], [], 1
    for w in words:
        cur.append(w)
        duration = cur[-1]["end"] - cur[0]["start"]
        ends_sentence = w["word"].rstrip().endswith((".", "?", "!"))
        if len(cur) >= max_words or duration >= max_seconds or ends_sentence:
            cues.append(cur)
            cur = []
    if cur:
        cues.append(cur)

    lines = []
    for i, g in enumerate(cues, start=1):
        text = " ".join(w["word"] for w in g).replace("\n", " ")
        lines.append(str(i))
        lines.append(f"{_srt_ts(g[0]['start'])} --> {_srt_ts(g[-1]['end'])}")
        lines.append(text)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
