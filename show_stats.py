"""Print real channel stats and the winners fed into topic research."""
from pipeline import analytics

stats = analytics.video_stats()
print("--- real channel stats ---")
for s in sorted(stats, key=lambda d: d["views"], reverse=True):
    print(f"{s['views']:>5} views  {s['likes']:>3} likes  {s['topic']}")
print()
print("winners fed to research:", analytics.winners(5))
