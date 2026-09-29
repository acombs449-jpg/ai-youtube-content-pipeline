"""Cross-post a rendered YouTube Short to TikTok via Blotato.

Rationale: the Shorts this pipeline already renders are 9:16 and <60s — natively
correct for TikTok — so distributing them there costs nothing extra to generate
and multiplies reach per unit of work. TikTok's FYP also gives new accounts far
more distribution than YouTube does, so it's the likelier source of a breakout.

Two hard-won details baked in (both discovered live on 2026-07-19/25 against the
TikTok agent's own Blotato integration — do not "simplify" these away):
  1. /v2/media takes an ALREADY-PUBLIC url; a local file needs the separate
     presigned flow (POST /v2/media/uploads -> PUT raw bytes -> use publicUrl).
  2. The PUT must send bytes, not a file handle. requests streams a handle with
     chunked transfer-encoding and no Content-Length, which the storage endpoint
     rejects mid-upload (ConnectionResetError 10054 on a real 28MB video).

NOTE on isDraft: Blotato documents it, but verified testing showed TikTok posts
submitted with isDraft=true went LIVE anyway. Treat every call here as
publishing immediately — there is no working "stage for review" path.
"""
import time
from pathlib import Path

import requests
import config

_UPLOAD_INIT = "https://backend.blotato.com/v2/media/uploads"
_POST = "https://backend.blotato.com/v2/posts"


def _upload(video_path: Path, attempts: int = 3) -> str:
    """Presigned-upload a local file; returns its public URL.

    Retries the WHOLE init+PUT cycle, not just the PUT: a reset mid-transfer can
    leave the presigned URL in an indeterminate state, so a clean one is safer
    than reusing it. Observed live — a 13MB PUT died with ConnectionResetError
    10054 while init returned a healthy 201, i.e. transient transport failure,
    exactly what a retry is for.
    """
    headers = {"blotato-api-key": config.BLOTATO_API_KEY,
               "Content-Type": "application/json"}
    body = video_path.read_bytes()  # bytes, not a handle — see module docstring
    last = None
    for attempt in range(attempts):
        try:
            init = requests.post(_UPLOAD_INIT, headers=headers,
                                 json={"filename": video_path.name}, timeout=30)
            init.raise_for_status()
            data = init.json()
            put = requests.put(data["presignedUrl"], data=body,
                               headers={"Content-Type": "video/mp4"}, timeout=300)
            put.raise_for_status()
            return data["publicUrl"]
        except Exception as e:
            last = e
            if attempt < attempts - 1:
                wait = 5 * (attempt + 1)
                print(f"    upload attempt {attempt + 1} failed ({type(e).__name__}); "
                      f"retrying in {wait}s")
                time.sleep(wait)
    raise last


def _caption(meta: dict) -> str:
    """TikTok caption from the video's own metadata. Hashtags matter far more
    for discovery on TikTok than on YouTube, so the tags are reused as tags."""
    title = meta.get("title", "").strip()
    tags = meta.get("tags", []) or []
    # TikTok hashtags: no spaces, capped so the caption stays readable.
    hashtags = []
    for t in tags[:6]:
        cleaned = "".join(ch for ch in t if ch.isalnum())
        if cleaned:
            hashtags.append("#" + cleaned.lower())
    for base in ("#money", "#personalfinance", "#moneytips"):
        if base not in hashtags:
            hashtags.append(base)
    return f"{title}\n\n{' '.join(hashtags[:10])}"


def to_tiktok(video_path, meta: dict) -> str | None:
    """Publish a rendered Short to TikTok. Returns the submission id, or None
    if cross-posting is disabled/unconfigured. Never raises — a TikTok failure
    must not fail an otherwise-successful YouTube upload."""
    if not config.CROSSPOST_TO_TIKTOK:
        return None
    if not config.BLOTATO_API_KEY or not config.BLOTATO_TIKTOK_ACCOUNT_ID:
        print("  - crosspost skipped: Blotato not configured")
        return None

    try:
        media_url = _upload(Path(video_path))
        body = {
            "post": {
                "accountId": config.BLOTATO_TIKTOK_ACCOUNT_ID,
                "content": {
                    "text": _caption(meta),
                    "mediaUrls": [media_url],
                    "platform": "tiktok",
                },
                "target": {
                    "targetType": "tiktok",
                    "privacyLevel": "PUBLIC_TO_EVERYONE",
                    "disabledComments": False,
                    "disabledDuet": False,
                    "disabledStitch": False,
                    "isBrandedContent": False,
                    "isYourBrand": True,
                    # Required disclosure: this content is AI-generated.
                    "isAiGenerated": True,
                    "isDraft": False,
                },
            }
        }
        r = requests.post(
            _POST,
            headers={"blotato-api-key": config.BLOTATO_API_KEY,
                     "Content-Type": "application/json"},
            json=body, timeout=120,
        )
        r.raise_for_status()
        pid = r.json().get("postSubmissionId")
        print(f"  - cross-posted to TikTok (live) [{pid}]")
        return pid
    except Exception as e:
        print(f"  - crosspost to TikTok failed (YouTube upload unaffected): {e}")
        return None
