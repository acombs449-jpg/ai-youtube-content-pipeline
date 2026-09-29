"""Step 6: upload to YouTube via the Data API v3 (true auto-publish).

First run opens a browser once to authorize, then saves token.json and refreshes
it automatically forever after. See README for the one-time Google Cloud setup.
"""
from pathlib import Path
import config

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # playlists + thumbnails + captions
    "https://www.googleapis.com/auth/yt-analytics.readonly",  # real retention/watch-time data
]


def _credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_path = config.ROOT / config.YOUTUBE_TOKEN
    secret_path = config.ROOT / config.YOUTUBE_CLIENT_SECRET
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not secret_path.exists():
                raise SystemExit(
                    f"Missing {secret_path.name}. Download OAuth client secret from "
                    "Google Cloud Console (see README) and place it here."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _service():
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_credentials())


def _analytics_service():
    """The YouTube Analytics API (v2) — separate service from the Data API v3
    above, but shares the same OAuth token/scopes."""
    from googleapiclient.discovery import build
    return build("youtubeAnalytics", "v2", credentials=_credentials())


def upload(video_path, meta: dict, privacy: str = "private",
           made_for_kids: bool = False, publish_at: str | None = None) -> str:
    """Upload one video. Returns the video id.

    privacy: 'private' | 'unlisted' | 'public'. Default 'private' so nothing goes
    live until you've reviewed it; flip to 'public' (or set publish_at) when ready.
    """
    from googleapiclient.http import MediaFileUpload

    yt = _service()
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": made_for_kids}
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at  # ISO 8601, e.g. 2026-06-25T14:00:00Z

    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": meta["description"][:4900],
            "tags": meta.get("tags", [])[:15],
            "categoryId": "27",  # Education
        },
        "status": status,
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    print(f"  - uploaded: https://youtu.be/{vid}  (privacy={status['privacyStatus']})")
    return vid


def add_to_playlist(video_id: str, playlist_name: str) -> bool:
    """File an uploaded video into a channel playlist by name (playlists.json)."""
    import json
    pl_file = config.ROOT / "playlists.json"
    if not pl_file.exists():
        return False
    ids = json.loads(pl_file.read_text(encoding="utf-8"))
    pl_id = ids.get(playlist_name)
    if not pl_id:
        # tolerate loose matches (e.g. "Saving" vs "Saving Money")
        for name, i in ids.items():
            if playlist_name.lower() in name.lower() or name.lower() in playlist_name.lower():
                pl_id = i
                break
    if not pl_id:
        print(f"  - playlist '{playlist_name}' not found; skipping")
        return False
    try:
        yt = _service()
        yt.playlistItems().insert(
            part="snippet",
            body={"snippet": {
                "playlistId": pl_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }},
        ).execute()
        print(f"  - added to playlist: {playlist_name}")
        return True
    except Exception as e:
        print(f"  - playlist add failed: {e}")
        return False


def upload_captions(video_id: str, srt_path) -> bool:
    """Upload a real caption track built from the actual narration text —
    replaces reliance on YouTube's own auto-transcription, which can mis-hear
    names/terms (a real risk for Case Files' named people/companies)."""
    from googleapiclient.http import MediaFileUpload
    try:
        yt = _service()
        yt.captions().insert(
            part="snippet",
            body={"snippet": {
                "videoId": video_id, "language": "en",
                "name": "English", "isDraft": False,
            }},
            media_body=MediaFileUpload(str(srt_path), mimetype="application/octet-stream"),
        ).execute()
        print("  - real captions uploaded (not relying on YouTube auto-transcription)")
        return True
    except Exception as e:
        print(f"  - caption upload failed: {e}")
        return False


def set_thumbnail(video_id: str, image_path) -> bool:
    """Set a custom thumbnail. Requires a verified channel; fails gracefully."""
    from googleapiclient.http import MediaFileUpload
    try:
        yt = _service()
        yt.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(image_path)),
        ).execute()
        print("  - custom thumbnail set")
        return True
    except Exception as e:
        msg = str(e)
        if "verif" in msg.lower() or "403" in msg:
            print("  - thumbnail skipped: channel not verified for custom thumbnails "
                  "(verify at youtube.com/verify). Saved locally for manual upload.")
        else:
            print(f"  - thumbnail upload failed: {e}")
        return False
