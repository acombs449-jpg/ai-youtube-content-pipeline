"""Track ElevenLabs character usage locally, so the pipeline can't silently
blow the monthly quota.

Why local tracking rather than asking ElevenLabs: the API key is deliberately
scoped to text-to-speech only, so /v1/user returns 401 "missing permission
user_read". We can't query the real balance — but every script we voice is
saved in output/*.json, so summing this calendar month's narrations is an
accurate proxy for what we spent.

This matters because the failure mode is nasty and already happened once: when
ElevenLabs stops accepting calls, every scheduled run dies at the voiceover
step, and (before the exit-code fix) reported success — six days of content
were lost silently. Better to skip one video with a loud message than to burn
the quota and lose the rest of the month.
"""
import json
from datetime import datetime
from pathlib import Path

import config

# ElevenLabs Creator plan. If the plan changes, change this.
MONTHLY_CHAR_LIMIT = int(getattr(config, "ELEVENLABS_MONTHLY_CHARS", 100_000))
WARN_AT = 0.85   # start reporting headroom
BLOCK_AT = 0.97  # refuse to start another video


def used_this_month() -> int:
    """Sum narration characters for videos created in the current month."""
    prefix = datetime.now().strftime("%Y%m")
    total = 0
    for f in config.OUTPUT.glob("*.json"):
        # Files are named YYYYmmdd_HHMMSS_micro_<fmt>.json
        if not f.name.startswith(prefix):
            continue
        try:
            total += len(json.loads(f.read_text(encoding="utf-8")).get("narration", ""))
        except Exception:
            continue
    return total


def check(projected_chars: int = 800) -> tuple[bool, str]:
    """Return (ok_to_proceed, human-readable status)."""
    used = used_this_month()
    pct = used / MONTHLY_CHAR_LIMIT
    remaining = MONTHLY_CHAR_LIMIT - used
    status = (f"voice budget: {used:,}/{MONTHLY_CHAR_LIMIT:,} chars "
              f"({pct*100:.0f}%), ~{max(remaining,0)//800} videos left this month")
    if pct >= BLOCK_AT or remaining < projected_chars:
        return False, (status + " — STOPPING to protect the rest of the month. "
                       "Resets on the 1st; raise ELEVENLABS_MONTHLY_CHARS if the "
                       "plan was upgraded.")
    if pct >= WARN_AT:
        return True, status + " — running low"
    return True, status
