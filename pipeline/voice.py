"""Step 3: ElevenLabs TTS with character-level timestamps.
Returns the mp3 path and word-level timings."""
import base64
import time
import requests
import config

_API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps"


def synthesize(text: str, out_path) -> list[dict]:
    """Retries transient failures so an autonomous run isn't lost to a blip."""
    key = config.require("ELEVENLABS_API_KEY")
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    last = None
    for attempt in range(3):
        try:
            resp = requests.post(
                _API.format(voice=config.ELEVENLABS_VOICE_ID),
                headers={"xi-api-key": key, "Content-Type": "application/json"},
                json=body, timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            last = e
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
    else:
        raise last
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(data["audio_base64"]))
    return _chars_to_words(data["alignment"])


def _chars_to_words(alignment: dict) -> list[dict]:
    chars = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]
    words, cur, cur_start, prev_end = [], "", None, 0.0
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append({"word": cur, "start": cur_start, "end": prev_end})
                cur = ""
            continue
        if not cur:
            cur_start = s
        cur += ch
        prev_end = e
    if cur:
        words.append({"word": cur, "start": cur_start, "end": prev_end})
    return words
