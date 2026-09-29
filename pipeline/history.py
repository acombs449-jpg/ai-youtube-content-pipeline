"""Persistent record of topics already posted, so the agent never repeats."""
import json
import config

_FILE = config.ROOT / "history.json"

# Hard ceiling purely so the research prompt can't grow without bound. At ~12
# tokens per title this is a few thousand tokens — trivial next to the value of
# not republishing a topic — and at ~1 video/day it's over a year of runway.
MAX_TOPICS = 400


def recent(limit: int | None = None) -> list[str]:
    """Topics already covered, for the 'do not repeat' list.

    Defaults to the FULL history. It used to default to the last 30, which
    silently broke once the channel passed 30 videos: older topics scrolled out
    of the window and became eligible for regeneration again (caught 2026-07-26
    at 38 entries — 8 topics were already re-eligible). Dedup is only meaningful
    if it remembers everything.
    """
    if not _FILE.exists():
        return []
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    topics = [e["topic"] for e in data if e.get("topic")]
    if limit is not None:
        topics = topics[-limit:]
    return topics[-MAX_TOPICS:]


def add(topic: str, video_id: str | None = None):
    data = []
    if _FILE.exists():
        try:
            data = json.loads(_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = []
    data.append({"topic": topic, "video_id": video_id})
    _FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
