"""AI-generated B-roll via the Runway API — an alternative to Pexels stock
footage for higher production value, at real per-second cost.

Verified live 2026-07-19 directly against the official SDK source
(github.com/runwayml/sdk-python: api.md + types/task_retrieve_response.py)
and the developer pricing page (dev.runwayml.com) — not assumed. Key facts
that came out DIFFERENT from initial assumptions:
  - Endpoint is client.text_to_video.create(model=, prompt_text=, ratio=,
    duration=) -> object with .id. Valid text_to_video models do NOT include
    "gen4_turbo" (that's image_to_video only) - the real roster is gen4.5,
    veo3.1, veo3.1_fast, happyhorse_1_0, seedance2(*_fast/_mini),
    gemini_omni_flash, veo3.
  - Polling is client.tasks.retrieve(id) -> object with .status, one of
    PENDING/THROTTLED/RUNNING/CANCELLED/FAILED/SUCCEEDED. On SUCCEEDED,
    .output is a List[str] of download URLs that EXPIRE in 24-48h - must
    download immediately, not defer.
  - ratio only accepts exactly "1280:720" or "720:1280" (no other values).
  - Real per-second pricing (dev.runwayml.com, 2026-07-19): Gen-4.5 $0.12/s
    is Runway's own "balanced everyday" recommendation and the one used here
    - materially different from the $0.05/s figure first assumed/quoted.

contentModeration.publicFigureThreshold is deliberately left at Runway's
default ("auto", strict) rather than relaxed to "low" - a second layer of
defense on top of the Case Files "no real named individuals" rule already
built into the prompt keywords themselves.
"""
import time
import requests
import config

MODEL = "gen4.5"
PRICE_PER_SECOND = 0.12
POLL_SECONDS = 5
MAX_WAIT_SECONDS = 300

_CINEMATIC_WRAP = (
    "Cinematic B-roll shot: {keyword}. Professional lighting, shallow depth "
    "of field, smooth camera motion, high production value, no on-screen "
    "text, no logos, no readable text of any kind."
)


def _ratio(orientation: str) -> str:
    return "720:1280" if orientation == "portrait" else "1280:720"


def _client():
    from runwayml import RunwayML
    return RunwayML(api_key=config.require("RUNWAY_API_KEY"))


def generate_clip(keyword: str, out_path, orientation: str, duration: int = 8):
    """Generate one AI B-roll clip. Returns out_path on success, None on any
    failure/timeout — callers must fall back to stock footage gracefully."""
    client = _client()
    prompt = _CINEMATIC_WRAP.format(keyword=keyword)[:1000]  # API's 1000-char cap

    try:
        task = client.text_to_video.create(
            model=MODEL, prompt_text=prompt, ratio=_ratio(orientation),
            duration=duration,
        )
    except Exception as e:
        print(f"     ! runway submit failed for '{keyword}': {e}")
        return None

    waited = 0
    while waited < MAX_WAIT_SECONDS:
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
        try:
            result = client.tasks.retrieve(task.id)
        except Exception as e:
            print(f"     ! runway poll failed: {e}")
            return None

        if result.status == "SUCCEEDED":
            url = result.output[0]
            try:
                with requests.get(url, stream=True, timeout=180) as r:
                    r.raise_for_status()
                    with open(out_path, "wb") as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)
            except Exception as e:
                print(f"     ! runway download failed: {e}")
                return None
            cost = duration * PRICE_PER_SECOND
            print(f"     runway: '{keyword}' -> {out_path.name} (~${cost:.2f})")
            return out_path

        if result.status in ("FAILED", "CANCELLED"):
            reason = getattr(result, "failure", result.status)
            print(f"     ! runway generation failed for '{keyword}': {reason}")
            return None
        # PENDING / THROTTLED / RUNNING -> keep polling

    print(f"     ! runway timed out for '{keyword}' after {MAX_WAIT_SECONDS}s")
    return None


def generate_broll(visual_keywords: list[str], out_dir, want: int, orientation: str) -> list:
    """Same interface as visuals.fetch_broll() — drop-in swap. Any clip that
    fails generation is simply skipped (not retried with a different keyword),
    keeping cost predictable; caller should have Pexels as a fallback if the
    result list comes back short."""
    paths = []
    for i, kw in enumerate(visual_keywords[:want]):
        out = out_dir / f"runway_{i:02d}.mp4"
        if generate_clip(kw, out, orientation):
            paths.append(out)
    return paths
