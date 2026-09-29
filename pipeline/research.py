"""Step 1: finance video topic ideas from Claude as structured JSON.
Generates a large pool, scores each for click/watch potential, biases toward
the channel's proven winners AND real market-wide trend patterns, and returns
ideas best-first."""
import config
import spend
from .jsonutil import parse_or_retry

_PROMPT = """You are a YouTube strategist for a faceless personal-finance channel.
NICHE: {niche}
ANGLE: {angle}

Propose {n} {fmt} video ideas likely to perform. Favor specific, concrete,
beginner-friendly money topics with a clear payoff. Educational only — NEVER
specific investment picks, "get rich" promises, or guaranteed returns.
{length_rule}

{proven_format}

PROVEN WINNERS on this exact channel (real view data — make more ideas with
similar angles/energy, but NOT the same topic):
{winners}

HIGH-RETENTION videos on this channel (real watch-time data — people who
click AND actually watch through; this is what YouTube's algorithm rewards
most, weight this signal heavily):
{retention}

LOW-RETENTION videos on this channel (real data — people clicked but did NOT
finish these; low watch-through actively suppresses reach). Read these
carefully, because there are two different lessons here:
  * If a video got MANY views but low retention, the title/hook WORKED — the
    content failed to pay it off. Don't abandon that subject; if you revisit
    it, come at it from a genuinely different angle with a concrete, satisfying
    payoff the previous version clearly lacked.
  * If a video got FEW views AND low retention, it simply didn't land. Avoid
    that territory.
{low_retention}

MARKET-WIDE PATTERNS currently working across finance YouTube (real data from
top-performing videos this month — use these to shape angle/framing, not to
copy any specific video):
{market_trends}

ALREADY COVERED — do NOT repeat or closely overlap these; bring something
genuinely fresh:
{avoid}

MOST RECENT TITLES (newest first). Look at their STRUCTURE, not just their
subject: if they share a repeated opening or phrasing pattern, you must break
it. Proposing another variation of the same construction is a failure, even on
a new subject — near-identical titles fatigue viewers and compete with each
other for the same audience:
{recent_titles}

For each idea include viral_score: your honest 1-10 rating of its
stop-the-scroll + click potential for THIS niche (be harsh; most ideas are 5-6)."""

# response schema — enforced server-side via output_config.format, so the
# prompt above no longer has to spell out "Return ONLY valid JSON" itself
# (see 2026-09 Claude API audit; jsonutil.extract_json's fence-stripping and
# repair pass are no longer needed for this call, though jsonutil.py stays —
# market_trends.py and scriptgen.py still use it).
_IDEAS_SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "hook": {"type": "string"},
                    "angle": {"type": "string"},
                    "why_now": {"type": "string"},
                    "viral_score": {"type": "integer"},
                },
                "required": ["topic", "hook", "angle", "why_now", "viral_score"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ideas"],
    "additionalProperties": False,
}


def get_ideas(fmt_name: str, n: int = 3, avoid: list[str] | None = None,
              winners: list[str] | None = None,
              market_trends: list[str] | None = None,
              retention: list[str] | None = None,
              low_retention: list[str] | None = None) -> list[dict]:
    _short_budget = config.SHORT_BUDGET_SECONDS
    label = ("long-form (8-10 min)" if fmt_name == "long"
             else f"short (under {_short_budget}s)")
    # The market-trend signal actively promotes "5-10 item listicles", which is
    # sound advice for long-form but physically impossible in a Short — a 5-item
    # Short ran 64s and got rejected by the quality gate (2026-07-22). The topic
    # itself has to respect the format, since by the scripting stage the item
    # count is already baked into the title.
    if fmt_name == "short":
        length_rule = (
            f"\nHARD FORMAT LIMIT: these are ~{config.FORMATS['short']['target_seconds']}"
            f"-SECOND Shorts, written to come in under {_short_budget}s. Do NOT "
            "propose any topic that requires enumerating more than 3 items — a "
            "'5 things' or '7 mistakes' idea CANNOT be delivered properly in that "
            "time and will be cut down or rejected. If the market patterns below "
            "favor numbered lists, adapt that energy to 2-3 items MAX, or use a "
            "single-insight angle instead. One sharp, complete idea beats a rushed "
            "list every time."
        )
    else:
        length_rule = ""
    avoid_txt = "\n".join(f"- {t}" for t in (avoid or [])) or "(none yet)"
    winners_txt = "\n".join(f"- {w}" for w in (winners or [])) or "(no data yet)"
    trends_txt = "\n".join(f"- {t}" for t in (market_trends or [])) or "(no data yet)"
    retention_txt = "\n".join(f"- {r}" for r in (retention or [])) or "(no data yet)"
    low_txt = "\n".join(f"- {r}" for r in (low_retention or [])) or "(no data yet)"
    # Last 8 titles verbatim, newest first, so the model can see and deliberately
    # break repeated structure. Added after a rigid format rule collapsed 18 of 20
    # consecutive titles into "What X Actually..." and halved retention.
    recent_titles = "\n".join(f"- {t}" for t in reversed((avoid or [])[-8:])) or "(none yet)"
    pool = max(n * 3, 6)  # over-generate, keep only the best
    client = spend.tracked_client(config.require("ANTHROPIC_API_KEY"))
    # max_tokens raised 3000->6000 and the parse moved onto jsonutil's
    # retry-capable helper 2026-09-06: this call died with a JSONDecodeError
    # on truncated JSON at the default pool size (6 ideas), consistent with
    # the account now spending part of a fixed token budget on an unrequested
    # thinking block before the JSON — see jsonutil._text_of. parse_or_retry
    # extracts the text block by type (not position) and re-prompts once if
    # the result still doesn't parse, instead of crashing the run outright.
    result = parse_or_retry(
        client,
        model=config.RESEARCH_MODEL,
        max_tokens=6000,
        system=config.SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": _IDEAS_SCHEMA}},
        messages=[{"role": "user", "content": _PROMPT.format(
            niche=config.NICHE, angle=config.NICHE_ANGLE, n=pool, fmt=label,
            avoid=avoid_txt, winners=winners_txt, market_trends=trends_txt,
            retention=retention_txt, low_retention=low_txt,
            length_rule=length_rule, proven_format=config.PROVEN_FORMAT,
            recent_titles=recent_titles,
        )}],
        label="ideas",
    )
    ideas = result["ideas"]
    ideas.sort(key=lambda i: i.get("viral_score", 0), reverse=True)
    best = ideas[:n] if n < len(ideas) else ideas
    for i in best:
        print(f"     pick: {i['topic']} (viral {i.get('viral_score', '?')}/10)")
    return best
