"""Orchestrator for the finance YouTube agent.

Usage:
    python run.py --format short            # 1 Short, saved locally (no upload)
    python run.py --format long             # 1 long-form video
    python run.py --format short --n 3      # 3 Shorts
    python run.py --format short --upload    # upload as PRIVATE for review
    python run.py --format long --upload --privacy public   # go live

Videos default to PRIVATE on upload so nothing publishes before you review it.
"""
import argparse
import json
import shutil
import time
from datetime import datetime

import config
from pipeline import (research, scriptgen, voice, visuals, captions, render,
                      quality, youtube_upload, history, thumbnails, analytics,
                      market_trends, case_studies, yt_analytics, runway,
                      crosspost, budget)


def _pick_related(idea_topic: str, wins: list[str], avoid: list[str]) -> str | None:
    """Pick a real other video to reference in the 'bridge' ending CTA."""
    for w in wins:
        topic = w.split(" (")[0]
        if topic.lower() != idea_topic.lower():
            return topic
    for t in reversed(avoid):
        if t.lower() != idea_topic.lower():
            return t
    return None


def make_one(idea, fmt_name, args, related_video=None):
    f = config.fmt(fmt_name)
    slug = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # microseconds = collision-proof for concurrent runs
    work = config.WORK / slug
    work.mkdir(parents=True, exist_ok=True)
    print(f"\n=== [{fmt_name}] {idea['topic']} ===")

    print("  writing script...")
    try:
        script = scriptgen.write_script(idea, fmt_name, related_video=related_video)
    except scriptgen.ScriptTooLong as e:
        # Same rejection the post-render quality gate used to make, taken here
        # instead — before ElevenLabs quota, B-roll downloads and an ffmpeg
        # render get spent on a video that was always going to be thrown away.
        print(f"     SKIP (pre-render): {e}")
        # Record the topic for the same reason the quality-gate path does:
        # otherwise the idea gets re-picked and burns a cycle again next run.
        history.add(idea["topic"], None)
        shutil.rmtree(work, ignore_errors=True)
        return None

    print("  voiceover...")
    audio = work / "narration.mp3"
    words = voice.synthesize(script["narration"], audio)

    if fmt_name in config.USE_RUNWAY_FOR:
        print("  generating AI B-roll (Runway, real cost)...")
        broll = runway.generate_broll(script["visual_keywords"], work,
                                      want=f["broll_count"], orientation=f["orientation"])
        if len(broll) < f["broll_count"]:
            print(f"  runway supplied {len(broll)}/{f['broll_count']}; filling the rest from Pexels...")
            broll += visuals.fetch_broll(
                script["visual_keywords"][len(broll):], work,
                want=f["broll_count"] - len(broll), orientation=f["orientation"])
    else:
        print("  fetching B-roll...")
        broll = visuals.fetch_broll(script["visual_keywords"], work,
                                    want=f["broll_count"], orientation=f["orientation"])
    if not broll:
        raise SystemExit("No B-roll downloaded; check Pexels/Runway key or keywords.")

    print("  render...")
    ass = captions.build_ass(words, work / "captions.ass") if f["burn_captions"] else None
    out = config.OUTPUT / f"{slug}_{fmt_name}.mp4"
    render.render(broll, audio, ass, out, work, f)

    meta = {
        "title": script["title"],
        "description": script["description"],
        "tags": script.get("tags", []),
        "chapters": script.get("chapters", []),
        "format": fmt_name,
        "created": slug,
        # Kept so a high-retention video can actually be studied later. Trying to
        # reverse-engineer the channel's best performer (APR, 140% watched) on
        # 2026-07-26 was only possible from its title, because the script it was
        # built from was never saved.
        "narration": script.get("narration", ""),
    }
    (config.OUTPUT / f"{slug}_{fmt_name}.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  -> {out}")

    # Custom thumbnail (long-form / case study benefit most from CTR).
    thumb = None
    if fmt_name in ("long", "case_study"):
        thumb = config.OUTPUT / f"{slug}_{fmt_name}.jpg"
        thumbnails.make(script.get("thumbnail_text", ""), thumb)
        print(f"  thumbnail -> {thumb.name}")

    print("  quality gate...")
    passed, problems = quality.check(out, f)
    if not passed:
        for p in problems:
            print(f"     FAIL: {p}")
        print("     -> not uploading; review manually.")
        # Still record the topic — otherwise a failing idea gets re-picked
        # and re-generated (wasting a full cycle) on every subsequent run.
        history.add(idea["topic"], None)
        if fmt_name == "case_study":
            case_studies.mark_done(idea["topic"], None)
        shutil.rmtree(work, ignore_errors=True)
        # Falsy: a quality-gate rejection is NOT a success. Returning the path
        # here (truthy) previously made main() count rejected videos as wins and
        # exit 0 — the same false-green-light bug the exit code was added to catch.
        return None
    print("     passed")

    vid = None
    if args.upload:
        print("  uploading to YouTube...")
        vid = youtube_upload.upload(out, meta, privacy=args.privacy)
        if vid and thumb:
            youtube_upload.set_thumbnail(vid, thumb)
        playlist = "Case Files" if fmt_name == "case_study" else script.get("playlist")
        if vid and playlist:
            youtube_upload.add_to_playlist(vid, playlist)
        if vid:
            # Real captions from the actual narration text, not YouTube's own
            # speech-to-text guess — matters most for named people/companies.
            srt = captions.build_srt(words, work / "real_captions.srt")
            youtube_upload.upload_captions(vid, srt)
        if fmt_name == "case_study":
            print("     -> REVIEW BEFORE PUBLISHING: this names real people/companies. "
                 "Watch it and fact-spot-check before flipping public.")

    # Cross-post Shorts to TikTok. Shorts only: the 9:16 <60s format is native
    # there, while long-form/case-study are 16:9 and far too long. Gated on a
    # real public YouTube upload so nothing private or rejected leaks out.
    if (fmt_name == "short" and vid and args.upload
            and args.privacy == "public"):
        crosspost.to_tiktok(out, meta)

    # Remember the topic so future runs don't repeat it.
    history.add(idea["topic"], vid)
    if fmt_name == "case_study":
        case_studies.mark_done(idea["topic"], vid)

    shutil.rmtree(work, ignore_errors=True)
    # When an upload was requested, success means it actually landed on YouTube.
    # Without this, a failed upload would still count as a win and exit 0.
    if args.upload and not vid:
        return None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["short", "long", "case_study"], required=True)
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--privacy", default="private",
                    choices=["private", "unlisted", "public"])
    args = ap.parse_args()

    avoid = history.recent()  # full history — see history.recent() docstring
    try:
        wins = analytics.winners(5)  # real channel data biases topic choice
        if wins:
            print("  proven winners: " + "; ".join(wins))
    except Exception as e:
        print(f"  (analytics unavailable: {e})")
        wins = []
    # Initialized up front so a failure fetching one signal can't discard the
    # other (both read the same cached report, but keep them independent).
    retention, low_retention = [], []
    try:
        retention = yt_analytics.best_retention(5)  # real watch-through data
        if retention:
            print("  high retention: " + "; ".join(retention))
        low_retention = yt_analytics.worst_retention(5)  # inverse signal
        if low_retention:
            print("  low retention (avoid/reframe): " + "; ".join(low_retention))
    except Exception as e:
        print(f"  (retention data unavailable: {e})")

    if args.format == "case_study":
        # Curated list, not AI-picked — real named people/companies stay
        # limited to what's been deliberately vetted in case_study_topics.json.
        print("picking from curated Case Files list "
             f"({case_studies.remaining_count()} remaining)...")
        ideas = []
        claimed = set()
        for _ in range(args.n):
            t = case_studies.next_topic(exclude=claimed)
            if not t:
                print("  - curated list exhausted; add more to case_study_topics.json")
                break
            ideas.append(t)
            claimed.add(t["topic"])
    else:
        print(f"researching {args.format} topics...")
        trends = market_trends.get_patterns()  # real market-wide signal, weekly-cached
        if trends:
            print("  market patterns: " + "; ".join(trends[:3]) + "...")
        ideas = research.get_ideas(args.format, n=args.n, avoid=avoid, winners=wins,
                                   market_trends=trends, retention=retention,
                                   low_retention=low_retention)

    succeeded = 0
    for idea in ideas[: args.n]:
        # Guard the ElevenLabs quota. Long-form/case-study cost ~9x a Short, so
        # project accordingly rather than assuming every video is cheap.
        projected = 7000 if args.format in ("long", "case_study") else 800
        ok, status = budget.check(projected)
        print(f"  {status}")
        if not ok:
            break
        related = _pick_related(idea["topic"], wins, avoid)
        try:
            if make_one(idea, args.format, args, related_video=related):
                succeeded += 1
        except Exception as e:
            print(f"  ! failed: {e}")
            if args.format == "case_study":
                case_studies.mark_done(idea["topic"], None)  # release the claim
        time.sleep(1)

    attempted = len(ideas[: args.n])
    print(f"\nDone. {succeeded}/{attempted} succeeded. Review videos in ./output.")

    # Exit non-zero when nothing at all got produced, so Task Scheduler reports
    # a real failure. Previously this always exited 0 even when every single
    # video failed — which is exactly how a 6-day outage (2026-07-20..26,
    # ElevenLabs payment failure + broken OAuth) went completely unnoticed:
    # the scheduler kept logging "result=0" success every single day.
    if attempted and succeeded == 0:
        print("ALL VIDEOS FAILED — exiting non-zero so this surfaces as a failure.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
