"""Configuration for the autonomous faceless personal-finance YouTube agent.
Supports two formats: SHORT (9:16 Shorts) and LONG (16:9 long-form)."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Strategy ---------------------------------------------------------------
NICHE = "personal finance and money tips for everyday people"
NICHE_ANGLE = (
    "Clear, practical money education: budgeting, saving, debt, credit, simple "
    "investing concepts. Beginner-friendly, no jargon, no hype. Educational only. "
    "Flagship recurring angle, favor when it fits: making money with AI — real "
    "tools, workflows, and side-hustle mechanics, hedged like any other income "
    "claim, no guaranteed-earnings language. Keep range beyond it so research "
    "doesn't run out of ideas."
)

# --- AI persona / operating mandate ------------------------------------------
# Applied as the `system` prompt on every Claude call in the pipeline (research,
# concept, scripting, polish, market-trend summarization). Sets ambition and
# ownership; the per-task instructions in each prompt carry the specific,
# non-negotiable compliance rules (YMYL disclaimers, Case Files factual rules)
# that this persona is explicitly instructed to treat as part of the job, not
# as friction against it.
#
# NOTE for Austin: this is deliberately editable. If you want the emphasis
# shifted (e.g. lean harder into affiliate/monetization angles, or dial back
# aggressiveness), rewrite this paragraph — it flows straight into every
# script the pipeline generates.
SYSTEM_PROMPT = (
    "You are the master architect and lead growth engineer for this channel's "
    "content operation — an elite YouTube content strategist and production "
    "director, the caliber of rigor and ownership you'd bring as a senior "
    "engineer at a top-5 Fortune 500 company. You are not a chatbot; you are "
    "an autonomous content machine. Your mandate: maximize legitimate audience "
    "growth (views, watch time, subscribers) and revenue, and get this channel "
    "to full monetization as fast as possible. Every video must pass the "
    "3-second hook test — the opening must make scrolling away feel like "
    "missing out — and earn the subscribe, not just ask for it.\n\n"
    "Write with confidence: strong, specific, punchy delivery, not vague or "
    "wishy-washy filler. That confidence is about STYLE, not about invented "
    "certainty — where a task's instructions call for hedged or attributed "
    "language (an unproven claim, a disputed allegation about a real person, "
    "any financial outcome or return), that hedging is content you must "
    "preserve exactly, not weak language to eliminate. A Fortune 500 company "
    "doesn't ship work that's legally exposed, factually sloppy, or promises "
    "outcomes it can't guarantee — that discipline IS part of the growth "
    "mandate, not a tax on it, because a channel struck down for "
    "misinformation or false claims earns zero long-term revenue. So: push "
    "hard on hooks, retention, and click appeal; never push on the accuracy, "
    "disclaimer, hedging, or safety rules stated in the task — those are the "
    "floor, not a suggestion."
)

# --- Brand / growth ---------------------------------------------------------
# Recurring identity drives subscribers: viewers follow a SERIES, not random tips.
CHANNEL_NAME = "The Daily Drop"
SERIES_NAME = "The Daily Drop"
# A reason-based CTA converts far better than "please subscribe".
SUBSCRIBE_REASON = "subscribe to The Daily Drop for a money win every single day"

# --- Format guidance --------------------------------------------------------
# HISTORY, so this mistake isn't repeated: on 2026-07-26 a rigid "always frame
# it as a concrete dollar consequence" rule was added here, extrapolated from a
# single outlier (the APR video, 140% watched on only 93 views). Measured two
# days and 9 videos later, it BACKFIRED:
#
#   OLD, varied phrasing : 26 videos | 2,415 views | 46.6% retention | 5 subs
#   NEW, rigid formula   :  9 videos |   723 views | 26.2% retention | 0 subs
#
# Retention nearly halved. The cause was formula collapse: 18 of 20 consecutive
# titles became "What [X] Actually...", 11 of them literally "Actually Costs
# You", and 11 of 20 were credit-card interest. Near-identical videos fatigue
# the viewer, cannibalize each other for the same audience, and read as
# templated to the platforms.
#
# The real lesson is NOT "dollar amounts win" — it is that the channel's
# genuinely strong videos were VARIED and each answered a real question with a
# stake attached: "The One Number That Tells If You Can Afford Something" (80%),
# "What a Charge-Off Actually Means" (66%), "Grace Period... And How to Use It"
# (62%), "Beneficiary... Why You Need One" (62%). Different shapes, different
# subjects, all useful. Optimize for that, and never let one phrasing dominate.
PROVEN_FORMAT = (
    "FORMAT GUIDANCE (from this channel's real retention data — treat as "
    "direction, NOT a template to copy):\n"
    "  * The videos that hold attention answer a real question and attach a "
    "genuine stake: what this means for the viewer, what it costs or saves "
    "them, or what to do about it. A concrete number helps when it fits "
    "naturally — but it is one tool, not the required shape.\n"
    "  * VARIETY IS MANDATORY. Do NOT reuse the title structure of recent "
    "videos. Rotate deliberately between different shapes: a surprising fact, "
    "a common mistake, a specific number, a 'most people don't realize...', a "
    "single practical action. If the last few titles all began the same way, "
    "you MUST use a different construction.\n"
    "  * VARY THE SUBJECT TOO. Do not stack multiple videos on the same narrow "
    "topic (e.g. several credit-card-interest videos in a row). Range across "
    "budgeting, saving, credit, debt, income, banking, and money habits.\n"
    "  * Purely definitional framing with no stake ('what X measures') "
    "underperforms — give the viewer a reason to care, not just a definition."
)

# YMYL safety: finance is scrutinized. Scripts must stay educational.
DISCLAIMER = (
    "This is educational content, not financial advice. Do your own research or "
    "talk to a licensed professional before making money decisions."
)

# Extra disclaimer for the "Case Files" series (real named companies/people —
# higher factual-accuracy stakes than routine tip content).
CASE_STUDY_DISCLAIMER = (
    "This video is an educational summary of publicly reported events, court "
    "records, and regulatory findings. It reflects public record and widely "
    "reported facts and is not a complete or exhaustive account. This is not a "
    "legal or professional opinion about any individual or organization named."
)

# --- Spoken length: MEASURED, not guessed ------------------------------------
# A rendered video's duration IS its narration's duration — render.py cuts the
# video to the length of the mp3 (`-t {audio_duration}`). So the ONLY lever on
# runtime is how many words the script contains, and length can be predicted
# from the script TEXT before a single character of TTS is spent.
#
# Measured 2026-07-28 across the 16 rendered Shorts whose narration text was
# saved (output/*_short.json + ffprobe on the matching .mp4):
#     words/sec  2.311 - 2.669   (mean 2.492)
#     chars/sec  12.63 - 14.70   (mean 13.74)
#     chars/word 5.48 average
# chars/sec at the SLOW end is the only estimator that never under-predicted on
# that sample (0/16 under; worst case +16% over). That asymmetry is exactly what
# a pre-spend guard wants: over-predicting costs one cheap text call, while
# under-predicting costs the full TTS quota + B-roll + render.
SPEECH_WPS_MEAN = 2.49
SPEECH_CPS_SLOW = 12.5      # deliberately under the slowest observed 12.63
CHARS_PER_WORD = 5.5

# VERIFIED 2026-07-28 against support.google.com/youtube/answer/10059070:
# YouTube's real Shorts ceiling is THREE MINUTES (raised from 60s on 2024-10-15).
# A 69s vertical video is still a Short. Do not let the old "YouTube won't count
# it" wording come back; it is false and it already caused one wasted diagnosis.
SHORTS_PLATFORM_MAX_SECONDS = 180

# THE DISCARD CEILING — raised 60 -> 90 on 2026-07-28 at Austin's instruction.
# This is the length past which a finished vertical video is thrown away. The old
# 60 was killing genuinely publishable videos: four real renders (60.33s, 60.79s,
# 63.95s, 69.24s) were binned as "too long" when every one of them was a valid,
# eligible Short. 90 was chosen deliberately:
#   * half the 180s platform limit — a full 90s of margin, not a boundary bet;
#   * clears the worst real overrun (69.24s) by ~21s, so ordinary model overshoot
#     no longer costs a render;
#   * still unmistakably SHORT-form (under 1.5 min), so the channel does not
#     silently become a 3-minute-video channel.
# IMPORTANT — this is a TOLERANCE, not a target. Generation is unchanged and
# still aims at FORMATS["short"]["target_seconds"] (42s) with the tighten budget
# below; typical output stays in the 30-60s band where this channel's completion
# rate actually lives. Re-TARGETING generation at longer videos would be a
# separate content-strategy decision (change target_seconds + SHORT_BUDGET_SECONDS)
# and has NOT been made.
SHORT_STRATEGY_MAX_SECONDS = 90

# Pre-render TIGHTEN budget — the length scriptgen aims the narration at, NOT the
# discard threshold (that is SHORT_STRATEGY_MAX_SECONDS above). A script whose
# worst-case estimate exceeds this gets rewritten shorter (a cheap text call)
# BEFORE any TTS, B-roll, or render spend. Because the estimator is an upper
# bound, 58s estimated lands ~48-58s real, which keeps the channel's proven
# short-form shape. A script that is still over 58s after the retries is now
# ACCEPTED (it is a valid Short) and only abandoned if it is over the 90s ceiling.
SHORT_BUDGET_SECONDS = 58
# 3, not 2: measured on the real 69s script, two rounds got 160 words -> 134
# (~60s) — closer but still over. Each round is one small text call; three of
# them are still orders of magnitude cheaper than one wasted render.
LENGTH_FIT_ATTEMPTS = 3


def estimate_seconds(narration: str) -> float:
    """Upper-bound spoken length of `narration` in seconds. Offline and free."""
    return len(narration or "") / SPEECH_CPS_SLOW


# --- Format profiles --------------------------------------------------------
FORMATS = {
    "short": {
        # 42s, down from 45 (2026-07-28). Measured: the model overshoots its
        # stated word count by ~25% (asked 108, delivered 112-160, mean 135), so
        # a 45s ask was really producing ~54s and clipping 60s on the tail. 42
        # plus the enforced budget above puts the mean back in the 30-60s band.
        "width": 1080, "height": 1920, "orientation": "portrait",
        "target_seconds": 42, "burn_captions": True, "broll_count": 6,
    },
    "long": {
        # >=8 min unlocks mid-roll ads (the real money on YouTube).
        "width": 1920, "height": 1080, "orientation": "landscape",
        "target_seconds": 510, "burn_captions": False, "broll_count": 16,
    },
    "case_study": {
        # Same technical specs as long-form; a bit more room for real depth.
        "width": 1920, "height": 1080, "orientation": "landscape",
        "target_seconds": 600, "burn_captions": False, "broll_count": 18,
    },
}
FPS = 30

# --- AI B-roll (Runway) -------------------------------------------------------
# Real cost, unlike free Pexels stock: ~$0.12/sec at the "gen4.5" model (see
# pipeline/runway.py for verified pricing/API details). Defaults to OFF for
# every format — add RUNWAY_API_KEY to .env AND list a format below to opt in.
# Start small: test with a single video before adding a format here.
# e.g. USE_RUNWAY_FOR = ["case_study"]   # highest production-value payoff, lowest volume
USE_RUNWAY_FOR = []

# --- API keys ---------------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "client_secret.json")
YOUTUBE_TOKEN = os.getenv("YOUTUBE_TOKEN", "token.json")

# --- Cross-posting -----------------------------------------------------------
# Shorts rendered here are 9:16 and well under TikTok's limit — natively correct
# for TikTok — so
# publishing them there too multiplies reach at zero extra generation cost.
# TikTok also gives new accounts far more algorithmic distribution than YouTube,
# making it the likelier place for a breakout.
# NOTE: this posts LIVE. Blotato's isDraft flag is documented but verified NOT
# to work for TikTok (posts went public anyway), so there is no review buffer.
CROSSPOST_TO_TIKTOK = os.getenv("CROSSPOST_TO_TIKTOK", "true").lower() == "true"
BLOTATO_API_KEY = os.getenv("BLOTATO_API_KEY", "")
BLOTATO_TIKTOK_ACCOUNT_ID = os.getenv("BLOTATO_TIKTOK_ACCOUNT_ID", "")

# --- Models -----------------------------------------------------------------
RESEARCH_MODEL = "claude-sonnet-5"
SCRIPT_MODEL = "claude-sonnet-5"

# --- Paths ------------------------------------------------------------------
ROOT = Path(__file__).parent
WORK = ROOT / "work"
OUTPUT = ROOT / "output"
WORK.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)


def fmt(name: str) -> dict:
    if name not in FORMATS:
        raise SystemExit(f"Unknown format '{name}'. Use one of: {list(FORMATS)}")
    return FORMATS[name]


def require(key_name: str) -> str:
    val = globals().get(key_name, "")
    if not val:
        raise SystemExit(f"Missing {key_name}. Copy .env.example to .env and fill it in.")
    return val
