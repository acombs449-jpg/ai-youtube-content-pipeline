"""Print channel-level stats: subscribers, total views, video count."""
from pipeline import youtube_upload

yt = youtube_upload._service()
r = yt.channels().list(part="statistics,snippet", mine=True).execute()
c = r["items"][0]
s = c["statistics"]
print(f"channel:     {c['snippet']['title']}")
print(f"subscribers: {s.get('subscriberCount', '?')}")
print(f"total views: {s.get('viewCount', '?')}")
print(f"videos:      {s.get('videoCount', '?')}")
