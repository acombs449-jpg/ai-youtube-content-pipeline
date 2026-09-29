"""One-time: run this to grant the new YouTube Analytics (retention data)
permission. Opens a browser tab -> click Allow -> done forever after.

Safe to run anytime: backs up the current working token first, so if
anything goes wrong the old token is restored automatically and nothing
that's currently working (uploads/thumbnails/playlists/captions) breaks.
"""
import shutil
import config
from pipeline import youtube_upload

token_path = config.ROOT / config.YOUTUBE_TOKEN
backup_path = config.ROOT / (config.YOUTUBE_TOKEN + ".bak")

if token_path.exists():
    shutil.copy(token_path, backup_path)
    token_path.unlink()

print("Opening a browser tab for you to approve the new Analytics permission...")
try:
    youtube_upload._service()
    print("SUCCESS — Analytics data is now active. Nothing else to do.")
except Exception as e:
    print(f"Something went wrong ({e}); restoring your previous working token.")
    if backup_path.exists():
        shutil.copy(backup_path, token_path)
    raise
