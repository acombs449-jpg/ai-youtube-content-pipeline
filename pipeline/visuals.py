"""Step 4: fetch free stock B-roll from Pexels in the right orientation."""
import requests
import config

_SEARCH = "https://api.pexels.com/videos/search"


def fetch_broll(keywords: list[str], out_dir, want: int, orientation: str) -> list:
    key = config.require("PEXELS_API_KEY")
    headers = {"Authorization": key}
    min_h = 1080 if orientation == "landscape" else 1280
    paths, i = [], 0
    while len(paths) < want and i < len(keywords) * 3:
        kw = keywords[i % len(keywords)]
        i += 1
        try:
            r = requests.get(_SEARCH, headers=headers, params={
                "query": kw, "orientation": orientation, "per_page": 5,
            }, timeout=60)
            r.raise_for_status()
            videos = r.json().get("videos", [])
        except Exception as e:
            print(f"  ! pexels '{kw}' failed: {e}")
            continue
        for v in videos:
            files = [f for f in v["video_files"] if f.get("height", 0) >= min_h] \
                or v["video_files"]
            best = max(files, key=lambda f: f.get("height", 0))
            dest = out_dir / f"broll_{len(paths):02d}.mp4"
            try:
                _download(best["link"], dest)
                paths.append(dest)
            except Exception as e:
                print(f"  ! download failed: {e}")
            if len(paths) >= want:
                break
    return paths


def _download(url, dest):
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
