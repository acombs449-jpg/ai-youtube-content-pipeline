"""Real market-wide trend signal: pulls top-performing PUBLIC finance videos
via the official YouTube Data API v3 search endpoint — this is the sanctioned,
ToS-compliant way to read public video metadata, not scraping. Claude then
summarizes the patterns/angles currently working across the niche.

Cached weekly (a search.list call costs real API quota) so this stays cheap
and never blocks the daily/weekly autonomous run. Fails silently to an empty
list on any error — the pipeline just falls back to its own channel data."""
import json
from datetime import datetime, timedelta, timezone

import config
import spend
from .jsonutil import parse_or_retry
from . import youtube_upload

CACHE_FILE = config.ROOT / "market_trends_cache.json"
MAX_AGE_DAYS = 7

SEARCH_QUERIES = [
    "personal finance tips",
    "money mistakes to avoid",
    "how credit works",
    "budgeting for beginners",
]

_SUMMARY_PROMPT = """Here are titles of top-performing personal finance videos
on YouTube published in the last 30 days (real search data, ranked by views):

{video_list}

Identify the 5-8 clearest PATTERNS in what's working right now: recurring
angles, title structures, or emotional hooks. Be specific and concrete (e.g.
"naming an exact dollar amount lost in the title" not "interesting numbers").

Return ONLY valid JSON: {{"patterns": ["...", "..."]}}"""


def _fetch_top_titles(max_per_query: int = 15) -> list[str]:
    yt = youtube_upload._service()
    published_after = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    titles = []
    for q in SEARCH_QUERIES:
        try:
            resp = yt.search().list(
                q=q, part="snippet", type="video", order="viewCount",
                publishedAfter=published_after, maxResults=max_per_query,
                relevanceLanguage="en", regionCode="US",
            ).execute()
        except Exception as e:
            print(f"  - market scan '{q}' failed: {e}")
            continue
        titles += [item["snippet"]["title"] for item in resp.get("items", [])]
    return titles


def _refresh() -> list[str]:
    titles = _fetch_top_titles()
    if not titles:
        return []
    listing = "\n".join(f"- {t}" for t in titles[:60])
    client = spend.tracked_client(config.require("ANTHROPIC_API_KEY"))
    patterns = parse_or_retry(
        client,
        model=config.RESEARCH_MODEL, max_tokens=1200,
        system=config.SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _SUMMARY_PROMPT.format(video_list=listing)}],
        label="market trends",
    ).get("patterns", [])
    CACHE_FILE.write_text(json.dumps(
        {"date": datetime.now(timezone.utc).isoformat(), "patterns": patterns},
        indent=2), encoding="utf-8")
    return patterns


def get_patterns() -> list[str]:
    """Weekly-cached market patterns. Never raises — degrades to [] so a scan
    failure can't block a scheduled upload."""
    try:
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            age = datetime.now(timezone.utc) - datetime.fromisoformat(data["date"])
            if age.days < MAX_AGE_DAYS:
                return data["patterns"]
        print("  - refreshing market trend scan (weekly, official YouTube API)...")
        return _refresh()
    except Exception as e:
        print(f"  - market trends unavailable: {e}")
        return []
