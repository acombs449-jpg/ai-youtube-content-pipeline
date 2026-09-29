"""One-time: create the 6 channel playlists via the API and save their IDs
to playlists.json so the pipeline can auto-assign future uploads."""
import json
import config
from pipeline import youtube_upload

PLAYLISTS = [
    ("Budgeting Basics",
     "Take control of every dollar. Simple budgeting methods for beginners — "
     "50/30/20, paycheck budgeting, and plans you'll actually stick to."),
    ("Saving Money",
     "Keep more of what you earn. Emergency funds, high-yield savings, cutting "
     "hidden fees, and saving tips that work on any income."),
    ("Crush Your Debt",
     "Get out of debt for good. Credit card payoff strategies, snowball vs "
     "avalanche, and the traps that keep people stuck."),
    ("Build Your Credit",
     "Raise your score and unlock better rates. How credit scores actually "
     "work, credit-building tips, and mistakes to avoid."),
    ("Investing for Beginners",
     "Make your money work for you. Index funds, compound interest, and "
     "plain-English investing basics. Educational only — not financial advice."),
    ("Money Habits & Mindset",
     "Think like someone who never goes broke. Daily money habits, psychology, "
     "and the small decisions that compound."),
    ("Case Files",
     "Deeply-researched breakdowns of real, well-documented financial "
     "collapses and fraud cases — how they happened, how they unraveled, and "
     "what they teach. Educational summaries of public record, not legal opinion."),
]


def main():
    yt = youtube_upload._service()
    existing = {}
    # Don't duplicate if re-run: list current playlists first.
    resp = yt.playlists().list(part="snippet", mine=True, maxResults=50).execute()
    for item in resp.get("items", []):
        existing[item["snippet"]["title"]] = item["id"]

    ids = {}
    for title, desc in PLAYLISTS:
        if title in existing:
            ids[title] = existing[title]
            print(f"exists: {title}")
            continue
        r = yt.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": desc},
                "status": {"privacyStatus": "public"},
            },
        ).execute()
        ids[title] = r["id"]
        print(f"created: {title}  ({r['id']})")

    (config.ROOT / "playlists.json").write_text(
        json.dumps(ids, indent=2), encoding="utf-8")
    print("\nSaved playlist ids -> playlists.json")


if __name__ == "__main__":
    main()
