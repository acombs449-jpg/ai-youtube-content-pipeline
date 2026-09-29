"""Weekly status report: YouTube channel + per-video stats (with week-over-week
deltas), winners, TikTok queue health. Writes reports/report_YYYYMMDD.md and
keeps a snapshot history in reports/snapshots.json for delta tracking."""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Windows consoles default to cp1252, which can't print em-dashes/emoji.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config
from pipeline import youtube_upload, analytics

REPORTS = config.ROOT / "reports"
REPORTS.mkdir(exist_ok=True)
SNAP_FILE = REPORTS / "snapshots.json"
TIKTOK_OUT = Path(os.getenv("TIKTOK_OUT", Path.home() / "tiktok-agent" / "output"))


def load_snapshots() -> list[dict]:
    if SNAP_FILE.exists():
        try:
            return json.loads(SNAP_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def channel_stats() -> dict:
    yt = youtube_upload._service()
    r = yt.channels().list(part="statistics", mine=True).execute()
    s = r["items"][0]["statistics"]
    return {
        "subs": int(s.get("subscriberCount", 0)),
        "views": int(s.get("viewCount", 0)),
        "videos": int(s.get("videoCount", 0)),
    }


def tiktok_queue() -> dict:
    vids = sorted(TIKTOK_OUT.glob("*.mp4"))
    oldest_days = None
    if vids:
        oldest = min(v.stat().st_mtime for v in vids)
        oldest_days = (datetime.now().timestamp() - oldest) / 86400
    return {"queued": len(vids), "oldest_days": oldest_days}


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    ch = channel_stats()
    vids = analytics.video_stats()
    vids.sort(key=lambda d: d["views"], reverse=True)
    tt = tiktok_queue()

    snaps = load_snapshots()
    prev = snaps[-1] if snaps else None
    prev_videos = {v["video_id"]: v["views"]
                   for v in prev.get("per_video", [])} if prev else {}

    lines = [f"# Weekly Content Report — {today}", ""]

    # --- Channel summary with deltas ---
    lines.append("## YouTube — The Daily Drop")
    if prev:
        lines.append(f"- Subscribers: **{ch['subs']}** ({ch['subs'] - prev.get('subs', 0):+d} this week)")
        lines.append(f"- Total views: **{ch['views']}** ({ch['views'] - prev.get('views', 0):+d} this week)")
        prev_count = prev.get("video_count", prev.get("videos", 0))
        if not isinstance(prev_count, int):
            prev_count = 0
        lines.append(f"- Videos: **{ch['videos']}** ({ch['videos'] - prev_count:+d} this week)")
    else:
        lines.append(f"- Subscribers: **{ch['subs']}**")
        lines.append(f"- Total views: **{ch['views']}**")
        lines.append(f"- Videos: **{ch['videos']}**")
    lines.append(f"- Progress to monetization: {ch['subs']}/1,000 subs "
                 f"({ch['subs'] / 10:.1f}%)")
    lines.append("")

    # --- Per-video table ---
    lines.append("## Videos by views (weekly gain)")
    lines.append("| Views | +Wk | Likes | Topic |")
    lines.append("|---|---|---|---|")
    for v in vids:
        gain = v["views"] - prev_videos.get(v["video_id"], 0) if prev else v["views"]
        lines.append(f"| {v['views']} | +{gain} | {v['likes']} | {v['topic']} |")
    lines.append("")

    # --- Winners the agent is steering toward ---
    wins = analytics.winners(5)
    lines.append("## Proven winners (auto-fed into topic research)")
    for w in wins:
        lines.append(f"- {w}")
    lines.append("")

    # --- TikTok queue health ---
    lines.append("## TikTok — The Daily Drop")
    lines.append(f"- Unposted videos in queue: **{tt['queued']}**")
    if tt["oldest_days"] is not None:
        lines.append(f"- Oldest queued video: {tt['oldest_days']:.0f} days old")
        if tt["oldest_days"] >= 3:
            lines.append("- ⚠️ **STALL: videos have been waiting 3+ days. "
                         "Post one today** (add trending sound, reply to comments).")
    elif tt["queued"] == 0:
        lines.append("- Queue EMPTY — run start.ps1 to generate a fresh batch.")
    lines.append("")

    # --- Action nudges ---
    lines.append("## This week")
    lines.append("- Reply to every YouTube comment (biggest algorithm signal).")
    lines.append("- Post 1 TikTok/day from the queue; refill with start.ps1.")
    lines.append("- Tell Claude which topics won this week to steer the agent harder.")

    report = "\n".join(lines)
    out = REPORTS / f"report_{today.replace('-', '')}.md"
    # utf-8-sig (BOM) so Notepad and PowerShell always render dashes/emoji right.
    out.write_text(report, encoding="utf-8-sig")

    # Save snapshot for next week's deltas (replace same-day snapshot on re-run).
    snap = {"date": today, "subs": ch["subs"], "views": ch["views"],
            "video_count": ch["videos"],
            "per_video": [{"video_id": v["video_id"], "views": v["views"]} for v in vids]}
    if snaps and snaps[-1].get("date") == today:
        snaps[-1] = snap
    else:
        snaps.append(snap)
    SNAP_FILE.write_text(json.dumps(snaps, indent=2), encoding="utf-8")

    print(report)
    print(f"\n[saved: {out}]")


if __name__ == "__main__":
    main()
