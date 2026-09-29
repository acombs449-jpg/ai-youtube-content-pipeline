"""Real retention/watch-time data via the YouTube Analytics API — a richer,
different data source than pipeline/analytics.py (which uses the Data API's
basic view/like counts). This is the metric that actually drives YouTube's
recommendation algorithm: a video with fewer views but a high percentage
watched is a BETTER template to learn from than a high-view, low-retention one.

Requires the yt-analytics.readonly OAuth scope (see youtube_upload.SCOPES).
Never raises — degrades to [] so a scan failure can't block a scheduled run.
"""
import json
from datetime import datetime, timedelta, timezone

import config
from . import youtube_upload

CACHE_FILE = config.ROOT / "retention_cache.json"
MAX_AGE_HOURS = 24  # analytics data updates roughly daily anyway


def _fetch() -> list[dict]:
    yta = youtube_upload._analytics_service()
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=90)
    resp = yta.reports().query(
        ids="channel==MINE",
        startDate=start.isoformat(),
        endDate=end.isoformat(),
        metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage",
        dimensions="video",
        # Must sort by -views: averageViewPercentage is a valid METRIC for the
        # video dimension but NOT a valid sort field (verified live 2026-07-26 —
        # sorting by it returns 400 "query is not supported"). Retention ranking
        # is done locally in best_retention() anyway, so nothing is lost.
        sort="-views",
        maxResults=50,
    ).execute()

    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    rows = []
    for row in resp.get("rows", []):
        d = dict(zip(headers, row))
        rows.append({
            "video_id": d.get("video"),
            "views": int(d.get("views", 0)),
            "avg_view_seconds": round(float(d.get("averageViewDuration", 0)), 1),
            "avg_view_percent": round(float(d.get("averageViewPercentage", 0)), 1),
        })
    return rows


def retention_report() -> list[dict]:
    """Cached ~daily. Joins in topic titles from history.json for readability."""
    try:
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            age = datetime.now(timezone.utc) - datetime.fromisoformat(data["date"])
            if age.total_seconds() < MAX_AGE_HOURS * 3600:
                rows = data["rows"]
            else:
                rows = _fetch()
                CACHE_FILE.write_text(json.dumps(
                    {"date": datetime.now(timezone.utc).isoformat(), "rows": rows},
                    indent=2), encoding="utf-8")
        else:
            rows = _fetch()
            CACHE_FILE.write_text(json.dumps(
                {"date": datetime.now(timezone.utc).isoformat(), "rows": rows},
                indent=2), encoding="utf-8")
    except Exception as e:
        print(f"  - retention data unavailable: {e}")
        return []

    hist_file = config.ROOT / "history.json"
    topics = {}
    if hist_file.exists():
        try:
            for e in json.loads(hist_file.read_text(encoding="utf-8")):
                if e.get("video_id"):
                    topics[e["video_id"]] = e["topic"]
        except Exception:
            pass
    # Any video not in history.json (early uploads, manual ones) would otherwise
    # surface as a bare ID like "v-VWmi71jvM" — useless as a learning signal,
    # since the model can't infer anything from an opaque string. Look the real
    # titles up from the API instead.
    unmapped = [r["video_id"] for r in rows if r["video_id"] not in topics]
    if unmapped:
        try:
            from . import youtube_upload
            yt = youtube_upload._service()
            for i in range(0, len(unmapped), 50):
                resp = yt.videos().list(
                    part="snippet", id=",".join(unmapped[i:i + 50])).execute()
                for item in resp.get("items", []):
                    topics[item["id"]] = item["snippet"]["title"]
        except Exception as e:
            print(f"  - couldn't resolve titles for {len(unmapped)} video(s): {e}")

    for r in rows:
        r["topic"] = topics.get(r["video_id"], r["video_id"])
    return rows


def best_retention(top: int = 5, min_views: int = 25) -> list[str]:
    """Videos people actually watch through, not just click — a stronger
    'what to make more of' signal than raw view count.

    min_views guards against noise: a 6-view video showing 168% retention is
    one person re-watching, not a repeatable pattern, and letting that outrank
    a 90-view video would teach the agent from a sample size of nothing.
    (Percentages CAN legitimately exceed 100% — that's Shorts looping, which
    is a genuine positive signal, just only trustworthy at real volume.)"""
    rows = [r for r in retention_report() if r["views"] >= min_views]
    if not rows:
        return []
    rows.sort(key=lambda r: r["avg_view_percent"], reverse=True)
    return [f"{r['topic']} ({r['avg_view_percent']}% watched, {r['views']} views)"
           for r in rows[:top]]


def worst_retention(bottom: int = 5, min_views: int = 25) -> list[str]:
    """Videos people click but DON'T finish — the inverse signal.

    Deliberately reports views alongside retention, because low retention has
    two very different causes and they need opposite responses:
      * HIGH views + low retention -> the title/hook earned the click but the
        content didn't pay it off. The topic is proven to attract; it's the
        delivery that failed. Worth revisiting with a better payoff.
      * LOW views + low retention -> weak on both ends; genuinely avoid.
    Flattening these into one 'bad topics' list would throw away that
    distinction and could discard the channel's best-performing hooks."""
    rows = [r for r in retention_report() if r["views"] >= min_views]
    if not rows:
        return []
    rows.sort(key=lambda r: r["avg_view_percent"])
    return [f"{r['topic']} (only {r['avg_view_percent']}% watched, {r['views']} views)"
           for r in rows[:bottom]]
