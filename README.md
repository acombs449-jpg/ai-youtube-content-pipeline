# Autonomous AI Video Pipeline: Personal-Finance YouTube Channel

An end-to-end, LLM-driven content system that researches, writes, voices, renders, quality-checks, and publishes YouTube videos with no human in the loop for routine content. It has been running in production on a daily schedule for **The Daily Drop**, a faceless personal-finance channel.

**Production results:** 160+ videos published autonomously, 16,000+ total views, running daily since mid-2026.

> Built and operated by Austin Combs. The design is mine: architecture, prompts, evaluation rules, and guardrails. The code was written with AI coding assistants under my direction and review.

---

## What it does

```
 ┌────────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐   ┌────────┐   ┌──────────────┐   ┌──────────┐
 │  Research  │──▶│ Concept  │──▶│  Script  │──▶│ Voice  │──▶│ Render │──▶│ Quality Gate │──▶│  Upload  │
 │ (LLM + real│   │ (title & │   │ (YMYL-   │   │ (TTS + │   │(ffmpeg,│   │ (ffprobe     │   │ (YouTube │
 │  analytics)│   │thumbnail │   │ safe,    │   │ word   │   │captions│   │  checks)     │   │ Data API)│
 └────────────┘   │ first)   │   │ length-  │   │ timing)│   │ B-roll)│   └──────────────┘   └────┬─────┘
       ▲          └──────────┘   │ budgeted)│   └────────┘   └────────┘                            │
       │                         └──────────┘                                                      ▼
       │                                                                             Playlist filing,
       └──────────────── performance feedback loop (views, retention) ◀──────────── captions, thumbnail,
                                                                                     TikTok cross-post
```

Three formats run on separate schedules:

| Format | Length | Schedule | Topic source |
|---|---|---|---|
| Short (9:16) | ~42s target, 58s budget | Daily | LLM research + channel analytics + market trends |
| Long-form (16:9) | ~8.5 min | Weekly | Same as above |
| Case Files | ~10 min | Manual only | Hand-curated list (see Guardrails) |

---

## Engineering highlights

**Closed-loop research using real data, not just model guesses.**
`research.py` has the LLM generate and score a large pool of ideas. It then biases the pool toward what the data says works: the channel's own top performers (`analytics.py`), high- and low-retention videos from the YouTube Analytics API (`yt_analytics.py`), and patterns across the whole niche pulled through the official Data API search endpoint (`market_trends.py`). The prompt treats two failure modes differently. A video with high views and low retention means the hook worked but the content fell short. A video with low views and low retention means the topic didn't land.

**Layered quality control, from cheapest to most expensive.**
Problems are caught as early as possible, before money is spent. `scriptgen.py` enforces the length budget from the script's word count, using measured speech-rate constants, *before* any text-to-speech or rendering cost. It retries up to three times to fit. `quality.py` is the last line of defence: it runs ffprobe on the rendered file to check duration against the platform and strategy limits, audio and video tracks, and resolution. A failed video is never uploaded.

**Robust LLM output parsing.**
`jsonutil.py` pulls structured JSON out of model responses reliably. It strips code fences, tolerates surrounding prose, and repairs the specific formatting defects seen in production logs. If parsing still fails, it re-prompts. This came from real failures in the scheduled runs, and the causes are documented in the code.

**Cost metering and budget guardrails.**
`spend.py` wraps the Anthropic client so every model call is metered automatically across all seven or more call sites. `budget.py` tracks text-to-speech character usage locally so the pipeline can't silently use up the monthly quota.

**Concept-first script generation.**
The title, thumbnail text, and hook angle are locked *before* the narration is written. This keeps the script focused on delivering what the title promises, which is the main driver of retention.

---

## Guardrails and responsible-AI decisions

Personal finance is "Your Money or Your Life" (YMYL) content, so accuracy matters.

- **Educational framing is enforced.** Scripts are instructed never to give specific investment picks, "get rich" promises, or guaranteed returns. A disclaimer is added to every video automatically.
- **Case Files use a curated list only.** Videos about real named companies and people (Enron, FTX, and so on) carry factual and legal risk. So their topics come *only* from a hand-maintained list of well-established public facts, and the model never picks them freely. The model is told to state only public record as fact, to hedge anything uncertain, and never to invent quotes or guess at motives. These videos are never auto-scheduled, and each one is reviewed by a person before it goes public.
- **Uploads are private by default.** Manual runs upload as private unless public is set explicitly.
- **Only official APIs are used.** Market data comes from the YouTube Data API. There's no scraping.

---

## Tech stack

- **Language:** Python 3
- **LLM:** Anthropic Claude API (research, trend analysis, scripting)
- **Voice:** ElevenLabs TTS with character-level timestamps (used for word-synced captions)
- **Video:** ffmpeg / ffprobe, Pexels stock B-roll, optional Runway AI-generated B-roll
- **Platform APIs:** YouTube Data API v3 (OAuth upload, playlists, captions, thumbnails), YouTube Analytics API, Blotato (TikTok cross-posting)
- **Automation:** Windows Task Scheduler, driving PowerShell runners with full per-run logging

## Project layout

```
run.py                 Orchestrator: runs one video end to end
config.py              Niche, formats, length budgets, models, disclaimers
spend.py               Automatic per-call LLM cost metering
weekly_report.py       Weekly channel + per-video performance report
pipeline/
  research.py          Idea generation + scoring with real performance signals
  market_trends.py     Niche-wide trend patterns via the official API
  analytics.py         View/like stats -> proven winners
  yt_analytics.py      Retention / watch-time data
  scriptgen.py         Concept-first, length-budgeted, YMYL-safe scripts
  jsonutil.py          Tolerant JSON extraction + repair for LLM output
  voice.py             TTS + word timings
  captions.py          Burned-in (.ass) and uploaded (.srt) captions
  visuals.py/runway.py B-roll sourcing
  render.py            ffmpeg assembly per format
  quality.py           Pre-upload validation gate
  thumbnails.py        Auto-generated thumbnails
  youtube_upload.py    OAuth upload, playlists, captions, thumbnails
  crosspost.py         TikTok distribution
  budget.py            TTS quota tracking
  case_studies.py      Curated Case Files topic queue
  history.py           Topic history (no repeats)
```

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env        # add your own API keys
python run.py --format short                    # generate one Short locally for review
python run.py --format short --upload           # upload as PRIVATE
python run.py --format long --upload --privacy public
```

It needs ffmpeg on PATH and a Google Cloud OAuth client (`client_secret.json`) for YouTube uploads. Credentials and tokens are git-ignored and never committed.
