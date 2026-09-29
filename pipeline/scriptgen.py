"""Step 2: write a finance script + YouTube metadata for either format.
Enforces YMYL safety (educational framing, disclaimer, no specific advice).

Concept-first workflow: the title/thumbnail/hook-angle get locked in BEFORE
the narration is written, so the script is built to deliver on a specific,
concrete promise rather than getting a catchy title bolted on after the fact.
"""
import anthropic
import config
import spend
from .jsonutil import parse_or_retry

_CONCEPT = """You are a YouTube thumbnail/title strategist for a faceless
personal-finance channel called {series}.
IDEA: {topic}
ANGLE: {angle}
FORMAT: {fmt_label}

Nail the CLICKABLE CONCEPT before any script gets written. The title and
thumbnail must promise something specific and curiosity-triggering enough
that clicking feels automatic — and the script will be written AFTER this to
deliver EXACTLY on what you promise here, so be concrete, not vague. No
clickbait lies — only promise what the video can genuinely deliver.
{format_constraint}

Provide:
- title: <=80 chars, curiosity-driven, a searchable keyword near the front
- thumbnail_text: 2-4 punchy words for the thumbnail image
- hook_angle: one sentence describing the EXACT payoff the opening seconds
  must deliver to match this title/thumbnail

Return ONLY valid JSON: {{"title": "...", "thumbnail_text": "...", "hook_angle": "..."}}"""

_SHORT = """Write a faceless YouTube Short script that delivers EXACTLY on
this locked concept:
TITLE (already decided — the script must pay this off): {locked_title}
REQUIRED OPENING PAYOFF: {locked_hook_angle}
TOPIC: {topic}
ANGLE: {angle}
CHANNEL/SERIES: {series} — every video is one quick, useful money win.

Requirements:
- LENGTH — this is measured and enforced automatically, not a suggestion:
  * TARGET ~{words} words (about {seconds}s spoken). Aim here.
  * HARD MAX {max_words} words. A script over that is programmatically
    rejected and rewritten before anything gets recorded, so write tight the
    first time. Err SHORTER, never longer.
  * Every extra sentence costs completion rate, which is what the algorithm
    actually rewards on this channel. Length is not depth.
  Open by delivering the required payoff above in the first line — no intro
  fluff.
- Punchy, conversational, ONE clear money tip delivered fast and completely.
- Educational only. No specific investments, no guaranteed-return claims.
- The whole point is to make the viewer think "if every video is this useful,
  I should follow." Deliver a complete, satisfying win — no half-answers.
- RETENTION ENGINEERING (this is what makes the algorithm push it):
  * First 2 seconds: a pattern interrupt — surprising claim, number, or question.
  * Middle: an open loop ("and the second part is what most people miss...")
    that keeps them watching to the end.
  * Every sentence earns the next one. Cut anything that doesn't.
  * Ending: land the payoff in the LAST sentence so watch-through hits 100%,
    and make the final line connect back to the hook so the video loops cleanly.
{proven_format}
{related_line}
- SUBSCRIBE CTA — this channel converts viewers to subscribers at only 0.2%,
  so a generic "follow for more tips" is measurably not working. Instead:
  * Open a CURIOSITY GAP about what's coming next — name a specific, concrete
    thing the viewer would lose money or miss out on by not seeing it
    (e.g. "tomorrow: the fee that costs the average person $340 a year").
  * Then land the ask naturally: "{subscribe_reason}".
  * It must feel like a genuine heads-up they'd want, never a plea. Do NOT
    promise anything the channel wouldn't actually cover.
- 4-6 visual_keywords: simple stock search terms (e.g. "counting cash",
  "person budgeting laptop", "credit card").
- on_screen_hook: 3-6 words for a text overlay in the first 2 seconds.
- description (2-3 sentences), 8-12 tags.
- playlist: exactly one of "Budgeting Basics", "Saving Money", "Crush Your Debt",
  "Build Your Credit", "Investing for Beginners", "Money Habits & Mindset".

Return ONLY valid JSON:
{{"narration": "...", "on_screen_hook": "...", "visual_keywords": ["..."],
  "description": "...", "tags": ["..."], "playlist": "..."}}"""

_LONG = """Write a faceless YouTube long-form script that delivers EXACTLY on
this locked concept:
TITLE (already decided — the script must pay this off): {locked_title}
REQUIRED OPENING PAYOFF: {locked_hook_angle}
TOPIC: {topic}
ANGLE: {angle}
CHANNEL/SERIES: {series} — practical money education people subscribe to.

Requirements:
- ~{seconds}s spoken (~{words} words) — this MUST be long enough for an 8-10
  minute video, so write a full, structured script with multiple sections.
- First 15 seconds must deliver the required payoff above AND preview what's
  coming ("by the end you'll know exactly X") so viewers commit to staying.
- Educational only. No specific investment picks, no guaranteed returns.
- RETENTION ENGINEERING (long-form dies to drop-off — this is what fights it):
  * Roughly every 60 seconds, insert a pattern-interrupt beat: a stat, a
    question, a tone shift, or a new visual angle — never let a stretch run
    long without one.
  * EVERY section transition is an open loop: end each section by teasing
    what's coming ("but here's where most people get it backwards...") so
    retention doesn't cliff at section boundaries — this is the #1 place
    long-form loses viewers.
  * Cut any sentence that doesn't earn the next one. No padding, no repeating
    yourself to hit a word count.
  * Ending: land the single biggest payoff in the final section, and reference
    the opening hook so the video feels complete, not just over.
{related_line}
- Subscribe CTA TWICE, worked in naturally: a soft one after the first valuable
  section (~90s in, reason-based: "{subscribe_reason}") and one at the end.
  Earn the subscribe by front-loading real value before asking.
- 12-18 visual_keywords spread across the script for varied B-roll.
- description (3-4 sentences + key points), 12-15 tags, and chapters
  (timestamp markers as a list of section titles in order).
- playlist: exactly one of "Budgeting Basics", "Saving Money", "Crush Your Debt",
  "Build Your Credit", "Investing for Beginners", "Money Habits & Mindset".

Return ONLY valid JSON:
{{"narration": "the full multi-section script", "visual_keywords": ["..."],
  "description": "...", "tags": ["..."], "chapters": ["..."], "playlist": "..."}}"""


_CASE_STUDY = """Write a faceless YouTube long-form "Case Files" script that
delivers EXACTLY on this locked concept:
TITLE (already decided — the script must pay this off): {locked_title}
REQUIRED OPENING PAYOFF: {locked_hook_angle}
SUBJECT: {topic}

KEY FACTS (your verified factual anchor — do not invent additional specific
facts, numbers, dates, or quotes beyond what's here or extremely well
established public record):
{facts_brief}

CHANNEL/SERIES: {series} Case Files — deeply-researched breakdowns of real,
well-documented financial collapses and fraud cases, told for entertainment
AND education.

CRITICAL FACTUAL-ACCURACY RULES (non-negotiable — higher stakes than normal
content because this names real people/companies):
- Only state as flat fact what is established public record (court verdicts,
  guilty pleas, regulatory findings, widely-corroborated reporting). For
  anything short of that certainty, use hedged, attributed language
  ("prosecutors alleged," "according to the SEC's findings," "reports at the
  time indicated") — never assert contested claims as bare fact.
- NEVER invent dialogue, quotes, internal thoughts, or specific conversations
  that aren't part of the documented record. No dramatized reenactment
  presented as literal fact.
- NEVER speculate about a real person's private motives, character, or
  intentions beyond what's legally established or their own public statements.
- Frame this as "here's what became public record and how it played out" —
  investigative/educational, not a personal character attack.
- If unsure whether a specific detail is solid, leave it out rather than
  risk stating something unverified as fact.

Requirements:
- ~{seconds}s spoken (~{words} words) — full structured script, chronological
  sections telling how it happened, was discovered, and its consequences.
- First 15 seconds: the required payoff above as a genuine hook — the scale,
  the twist, or the "how did nobody catch this" angle.
- RETENTION ENGINEERING:
  * Roughly every 60 seconds, a pattern-interrupt beat (a striking number, a
    turning point, "here's the moment it started to unravel").
  * Every section transition is an open loop into the next.
  * Ending: the single biggest lesson/takeaway, tied back to the opening hook.
{related_line}
- Subscribe CTA TWICE (reason-based: "{subscribe_reason}"), same as other
  long-form.
- 12-18 visual_keywords — GENERIC/ILLUSTRATIVE stock terms only (e.g.
  "courthouse exterior", "stock market red chart", "financial documents on
  desk", "judge gavel", "newspaper headlines generic", "city skyline finance
  district", "empty office boardroom"). Do NOT request footage of any specific
  real named individual — stock libraries won't have it and it must not be
  implied or faked.
- description (3-4 sentences + key points), 12-15 tags, chapters.

Return ONLY valid JSON:
{{"narration": "...", "visual_keywords": ["..."], "description": "...",
  "tags": ["..."], "chapters": ["..."]}}"""

_POLISH = """You are a ruthless YouTube retention editor. Score this opening
line for stop-the-scroll power (1-10, be harsh):

{first_line}

If below {threshold}, rewrite it to be dramatically stronger — same facts, no
clickbait lies.

Return ONLY valid JSON: {{"score": <int>, "first_line": "..."}}"""

POLISH_THRESHOLD = 8

_TIGHTEN = """This YouTube Short narration is too long. Spoken aloud it runs about
{est:.0f}s, and this channel's Shorts are built to land under {budget}s — that is
where its completion rate lives. Anything past {ceiling}s is discarded outright
before it is ever recorded.

Cut it to {max_words} words / {max_chars} characters or fewer — that is the
target, and coming in UNDER it is a success, not a problem. Non-negotiable rules:
- Keep the FIRST sentence as-is. It is the tested hook.
- Keep the closing payoff line and the subscribe CTA — the ending is what makes
  the video loop and convert.
- Cut by deleting hedges, restatements, wind-up phrases, second examples, and
  any sentence that does not earn the next one. Tighten wording.
- Do NOT drop the core answer, invent new claims, change the facts, or collapse
  it into a bare list. Same voice, same topic, same promise — just tighter.

NARRATION:
{narration}

Return ONLY valid JSON: {{"narration": "..."}}"""


class ScriptTooLong(Exception):
    """Script over the DISCARD CEILING after the retries — raised before TTS spend.

    Note the threshold: this is config.SHORT_STRATEGY_MAX_SECONDS (90s), not the
    58s tighten budget. Being over budget is not fatal — it just triggers a cheap
    rewrite, and a 62s Short that survives the rewrite is published, because it is
    a perfectly valid Short. Only a script that would still blow past the ceiling
    is abandoned here, which is the same rejection the post-render quality gate
    makes, moved to the only place it is free (an overrun used to be found after
    ElevenLabs quota, Pexels downloads and a full ffmpeg render were already paid
    for — ~21% of runs).
    """


def _max_words(budget_seconds: float) -> int:
    """Word cap equivalent to `budget_seconds` under the measured speech rate."""
    return int(budget_seconds * config.SPEECH_CPS_SLOW / config.CHARS_PER_WORD)


def _fit_length(client, script: dict, fmt_name: str) -> dict:
    """Steer a Short's narration toward the spoken-length budget, before TTS.

    Two DIFFERENT thresholds, deliberately:
      * budget  (config.SHORT_BUDGET_SECONDS, 58s) — what we aim at. Over it
        triggers a cheap rewrite, because short is what this channel's retention
        rewards.
      * ceiling (config.SHORT_STRATEGY_MAX_SECONDS, 90s) — what gets a script
        thrown away. Raised from 60 on 2026-07-28; a 62s Short is a valid Short
        and is no longer discarded just for missing the aim point.

    Cheap by construction: the estimate is pure arithmetic on the script text,
    and a rewrite is one small text call. Only Shorts have an upper bound —
    long-form and case studies need a MINIMUM, which the quality gate covers.
    """
    if fmt_name != "short":
        return script
    budget = config.SHORT_BUDGET_SECONDS
    ceiling = config.SHORT_STRATEGY_MAX_SECONDS
    rounds = 0  # ACTUAL tighten calls made — the loop can break out early
    for attempt in range(config.LENGTH_FIT_ATTEMPTS):
        est = config.estimate_seconds(script.get("narration", ""))
        if est <= budget:
            print(f"     length ok: ~{est:.1f}s estimated "
                  f"({len(script['narration'].split())} words, budget {budget}s)")
            return script
        # Ask for a cut well BELOW the budget, and ask harder each round.
        # Measured 2026-07-28 on the real 69s script: asked for 131 words, got
        # back 134 — the model under-delivers on a cut just as it overshoots on
        # generation, so aiming at the ceiling lands just over it. Undershooting
        # is harmless (a 45s Short is inside the channel's proven band); landing
        # at 60.3s is what throws the whole render away.
        ask = budget * (0.90 - 0.07 * attempt)
        print(f"     ~{est:.1f}s estimated (>{budget}s budget) — tightening to "
              f"~{ask:.0f}s before any TTS/render spend [attempt {attempt + 1}]")
        rounds += 1
        try:
            tightened = parse_or_retry(
                client,
                model=config.SCRIPT_MODEL, max_tokens=2000,
                system=config.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _TIGHTEN.format(
                    est=est, budget=budget, ceiling=ceiling, max_words=_max_words(ask),
                    max_chars=int(ask * config.SPEECH_CPS_SLOW),
                    narration=script["narration"],
                )}],
                label="tighten",
            ).get("narration", "").strip()
        except Exception as e:
            print(f"     (tighten call unparseable: {e})")
            break
        # Only accept a rewrite that actually helped. A model that returns the
        # same text, or somehow a longer one, must not overwrite a known state.
        if tightened and config.estimate_seconds(tightened) < est:
            script["narration"] = tightened
        else:
            print("     (tighten produced nothing shorter; stopping)")
            break

    est = config.estimate_seconds(script.get("narration", ""))
    words = len(script.get("narration", "").split())
    if est > ceiling:
        # Only a script that would blow the DISCARD CEILING is abandoned. The
        # estimator is an upper bound, so est <= ceiling guarantees the rendered
        # video comes in under it too — the post-render gate agrees by construction.
        # `rounds`, not LENGTH_FIT_ATTEMPTS: the loop breaks out early when a
        # tighten call comes back unparseable or no shorter, and claiming "after 3
        # attempts" when only 1 was made is the same species of lie as rounding a
        # threshold in the message that explains it.
        raise ScriptTooLong(
            f"narration still ~{est:.1f}s after {rounds} tighten "
            f"attempt(s) — over the {ceiling}s discard ceiling "
            f"({words} words). Skipped before TTS/B-roll/render — nothing was "
            "spent.")
    if est > budget:
        # The case the 60s cap used to throw a whole render away for.
        print(f"     length accepted: ~{est:.1f}s estimated — over the {budget}s "
              f"aim point but inside the {ceiling}s ceiling, so it ships "
              f"({words} words)")
        return script
    print(f"     length ok after tighten: ~{est:.1f}s estimated")
    return script


def _client() -> anthropic.Anthropic:
    return spend.tracked_client(config.require("ANTHROPIC_API_KEY"))


def _concept(client, idea: dict, fmt_name: str) -> dict:
    if fmt_name == "short":
        # Derived, never hardcoded: the concept step must be told the length the
        # script is actually written to, which is the tighten budget — not the
        # (higher) discard ceiling and not YouTube's 180s platform limit.
        fmt_label = (f"Short, ~{config.FORMATS['short']['target_seconds']}s spoken "
                     f"and under {config.SHORT_BUDGET_SECONDS} seconds total")
        constraint = (
            'If a numbered-list angle fits (e.g. "3 Things..."), cap it at 2-3 '
            "items MAX — a Short cannot do justice to more than that in the time "
            "available. A title promising 5+ items WILL cause the script to run "
            "over length and get rejected. Prefer one sharp insight over a long list."
            "\n\n" + config.PROVEN_FORMAT +
            "\n\nThe TITLE especially must reflect this: the channel's best title "
            "named a concrete cost ('What 24.99% Actually Costs You in Dollars'), "
            "while its worst were flat definitions and comparisons. Put the "
            "consequence or the dollar figure in the title itself."
        )
    elif fmt_name == "case_study":
        fmt_label = "long-form investigative case study, 8-10 minutes"
        constraint = (
            "This covers a real, well-documented financial collapse/fraud case. "
            "The title must promise the scale or twist of what happened WITHOUT "
            "sensationalizing beyond established facts — no clickbait lies about "
            "a real person/company. Curiosity-driven but accurate."
        )
    else:
        fmt_label = "long-form, 8-10 minutes"
        constraint = ("Numbered lists can go up to 8-10 items since there's room "
                      "to cover each with real depth.")
    return parse_or_retry(
        client,
        model=config.SCRIPT_MODEL, max_tokens=500,
        system=config.SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _CONCEPT.format(
            series=config.SERIES_NAME, topic=idea["topic"], angle=idea["angle"],
            fmt_label=fmt_label, format_constraint=constraint,
        )}],
        label="concept",
    )


def _polish_opening(client, script: dict) -> dict:
    """Score + auto-improve just the opening line (title is locked pre-concept
    and shouldn't drift from what the thumbnail already promised)."""
    narration = script["narration"].strip()
    first_line = narration.split(".")[0].strip() + "."
    try:
        v = parse_or_retry(
            client,
            model=config.SCRIPT_MODEL, max_tokens=400,
            system=config.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _POLISH.format(
                first_line=first_line, threshold=POLISH_THRESHOLD,
            )}],
            label="polish opening",
        )
    except Exception:
        return script
    print(f"     opening score: {v.get('score', '?')}/10")
    new_first = v.get("first_line", "").strip()
    if v.get("score", 10) < POLISH_THRESHOLD and new_first and first_line in narration:
        script["narration"] = narration.replace(first_line, new_first, 1)
        print("     -> opening line upgraded")
    return script


def write_script(idea: dict, fmt_name: str, related_video: str | None = None) -> dict:
    f = config.fmt(fmt_name)
    # Measured rate (config.SPEECH_WPS_MEAN), not the old hardcoded 2.4 guess.
    words = int(f["target_seconds"] * config.SPEECH_WPS_MEAN)
    client = _client()

    # 1) Lock the clickable concept BEFORE writing content.
    concept = _concept(client, idea, fmt_name)

    # 2) The "bridge" ending — reference a real other video instead of a
    #    generic sign-off, to chain into another session-lengthening watch.
    related_line = ""
    if related_video:
        related_line = (
            f'- BRIDGE ENDING: instead of "thanks for watching," tease a real '
            f'follow-up: something like "you now know this, but you\'ll want to '
            f'also see \'{related_video}\'" — reference that video by name naturally.'
        )

    if fmt_name == "case_study":
        template = _CASE_STUDY
    elif fmt_name == "long":
        template = _LONG
    else:
        template = _SHORT

    fmt_kwargs = dict(
        topic=idea["topic"], angle=idea.get("angle", ""),
        seconds=f["target_seconds"], words=words,
        # Shorts-only hard cap; str.format ignores it for the other templates.
        max_words=_max_words(config.SHORT_BUDGET_SECONDS),
        series=config.SERIES_NAME, subscribe_reason=config.SUBSCRIBE_REASON,
        # Shorts-only: this pattern was measured from Shorts retention (94% of
        # channel views), so it isn't generalized to long-form. Passing it as an
        # unused kwarg for the other templates is harmless — str.format ignores
        # extras — which keeps one shared kwargs dict.
        proven_format=config.PROVEN_FORMAT if fmt_name == "short" else "",
        locked_title=concept["title"], locked_hook_angle=concept["hook_angle"],
        related_line=related_line,
    )
    if fmt_name == "case_study":
        fmt_kwargs["facts_brief"] = idea.get("facts_brief", "")

    script = parse_or_retry(
        client,
        model=config.SCRIPT_MODEL,
        max_tokens=8000 if fmt_name in ("long", "case_study") else 2000,
        system=config.SYSTEM_PROMPT,
        messages=[{"role": "user", "content": template.format(**fmt_kwargs)}],
        label=f"{fmt_name} script",
    )

    # Title/thumbnail stay exactly what was locked in the concept step.
    script["title"] = concept["title"]
    if fmt_name in ("long", "case_study"):
        script["thumbnail_text"] = concept["thumbnail_text"]

    script = _polish_opening(client, script)

    # AFTER polish: the polish step rewrites the opening line and can lengthen
    # it, so the length budget has to be the last word on the narration text.
    script = _fit_length(client, script, fmt_name)

    # Always append the educational disclaimer to the description; case
    # studies about real people/companies get an extra one on top.
    disclaimer = config.DISCLAIMER
    if fmt_name == "case_study":
        disclaimer += "\n\n" + config.CASE_STUDY_DISCLAIMER
    script["description"] = script.get("description", "").rstrip() + "\n\n" + disclaimer
    return script
