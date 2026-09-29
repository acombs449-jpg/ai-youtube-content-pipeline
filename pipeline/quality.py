"""Quality gate: inspect the finished video before upload, per format.

This is the LAST line of defence, not the first: scriptgen enforces the Shorts
length budget from the script text before any TTS/render spend (see
scriptgen.ScriptTooLong). Anything caught here already cost a full render.
"""
import json
import shutil
import subprocess

import config

MIN_BYTES = 200_000


def _probe(path) -> dict:
    ffprobe = shutil.which("ffprobe")
    out = subprocess.check_output([
        ffprobe, "-v", "error", "-show_format", "-show_streams",
        "-of", "json", str(path),
    ])
    return json.loads(out)


def check(video_path, fmt) -> tuple[bool, list[str]]:
    problems = []
    if not video_path.exists() or video_path.stat().st_size < MIN_BYTES:
        return False, ["output file missing or too small"]
    try:
        info = _probe(video_path)
    except Exception as e:
        return False, [f"ffprobe failed: {e}"]

    dur = float(info.get("format", {}).get("duration", 0))
    # Durations print to 1dp on purpose. The old ":.0f" rendered a 60.33s video
    # as "60s" against a ">60" test, which reads as an off-by-one bug that isn't
    # there and cost a real diagnosis on 2026-07-27.
    if fmt["orientation"] == "portrait":
        if dur > config.SHORTS_PLATFORM_MAX_SECONDS:
            problems.append(
                f"not eligible as a Short: {dur:.1f}s exceeds YouTube's real "
                f"{config.SHORTS_PLATFORM_MAX_SECONDS}s Shorts ceiling")
        elif dur > config.SHORT_STRATEGY_MAX_SECONDS:
            # Deliberately NOT phrased as a platform rule. YouTube allows Shorts
            # up to 3 minutes (verified 2026-07-28); this rejection is the
            # channel's own short-form ceiling, raised 60 -> 90 on 2026-07-28
            # because the 60 was binning valid Shorts. Relaxing it further is a
            # strategy decision — change config.SHORT_STRATEGY_MAX_SECONDS, not
            # this line.
            problems.append(
                f"Short over the channel's {config.SHORT_STRATEGY_MAX_SECONDS}s "
                f"short-form ceiling: {dur:.1f}s. (YouTube itself allows up to "
                f"{config.SHORTS_PLATFORM_MAX_SECONDS}s — this is a strategy "
                "limit set in config.SHORT_STRATEGY_MAX_SECONDS, not a platform "
                "rule. Should have been caught pre-render by scriptgen.)")
        if dur < 15:
            problems.append(f"Short too short: {dur:.1f}s")
    else:
        if dur < 480:
            problems.append(f"long-form only {dur:.1f}s (<480s = no mid-roll ads)")

    streams = info.get("streams", [])
    if not any(s.get("codec_type") == "audio" for s in streams):
        problems.append("no audio track")
    vid = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not vid:
        problems.append("no video track")
    elif (vid.get("width"), vid.get("height")) != (fmt["width"], fmt["height"]):
        problems.append(
            f"wrong dimensions: {vid.get('width')}x{vid.get('height')} "
            f"(want {fmt['width']}x{fmt['height']})"
        )
    return (len(problems) == 0), problems
