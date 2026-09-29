"""Performance feedback: pull real view/like stats for past uploads and surface
the channel's proven winners so topic research can bias toward what works."""
import json
import config


def video_stats() -> list[dict]:
    """Return [{topic, video_id, views, likes}, ...] for history entries."""
    from . import youtube_upload, history as _h  # noqa: F401
    hist_file = config.ROOT / "history.json"
    if not hist_file.exists():
        return []
    entries = json.loads(hist_file.read_text(encoding="utf-8"))
    ids = [e["video_id"] for e in entries if e.get("video_id")]
    if not ids:
        return []
    yt = youtube_upload._service()
    stats = {}
    for i in range(0, len(ids), 50):
        resp = yt.videos().list(part="statistics", id=",".join(ids[i:i + 50])).execute()
        for item in resp.get("items", []):
            s = item.get("statistics", {})
            stats[item["id"]] = {
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
            }
    out = []
    for e in entries:
        vid = e.get("video_id")
        if vid and vid in stats:
            out.append({"topic": e["topic"], "video_id": vid, **stats[vid]})
    return out


def winners(top: int = 5) -> list[str]:
    """Top-performing topics by views (with likes as tiebreak)."""
    data = video_stats()
    if not data:
        return []
    data.sort(key=lambda d: (d["views"], d["likes"]), reverse=True)
    return [f"{d['topic']} ({d['views']} views)" for d in data[:top] if d["views"] > 0]
