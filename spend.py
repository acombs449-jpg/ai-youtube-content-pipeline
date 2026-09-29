"""What this pipeline is costing — mirrors trillion/tools/spend.py.

Wraps the Anthropic client so every .messages.create() call is metered
automatically, regardless of which pipeline module makes it. With 7+ call
sites scattered across research.py, market_trends.py, and scriptgen.py,
logging at each site individually is exactly the kind of thing that
silently drifts out of sync the next time a call site gets added — so the
client itself, not the call sites, is the seam.

Prices are per million tokens, from Anthropic's published rates, kept as
constants rather than fetched — so if they change, this becomes wrong,
which is why every figure returned is labelled an estimate.
"""
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import anthropic

USAGE_LOG = Path(__file__).parent / "usage.jsonl"

PRICES = {
    "claude-sonnet-5": {"in": 3.00, "out": 15.00, "cached_in": 0.30},
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00, "cached_in": 0.30},
}
_FALLBACK = {"in": 3.00, "out": 15.00, "cached_in": 0.30}


def _price(model: str) -> dict:
    for name, table in PRICES.items():
        if name in (model or ""):
            return table
    return _FALLBACK


def record(model: str, usage) -> None:
    """Append one call's usage. Appends rather than accumulating in memory,
    so the figure survives a restart — a spend number that resets whenever
    the process does is as useless as no number at all."""
    try:
        row = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": model,
            "in": getattr(usage, "input_tokens", 0) or 0,
            "out": getattr(usage, "output_tokens", 0) or 0,
            "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
            "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
        }
        with USAGE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass  # metering must never break a real run


def _cost(row: dict) -> float:
    p = _price(row.get("model"))
    # Cache WRITES cost 25% more than normal input; cache READS cost 90% less.
    return (
        row.get("in", 0) * p["in"] / 1e6
        + row.get("cache_write", 0) * p["in"] * 1.25 / 1e6
        + row.get("cache_read", 0) * p["cached_in"] / 1e6
        + row.get("out", 0) * p["out"] / 1e6
    )


def spend_report(days: int = 7) -> dict:
    """What's been spent, by day and by model."""
    if not USAGE_LOG.exists():
        return {
            "total_usd": 0.0,
            "note": "No usage recorded yet. Metering starts from the next API call.",
        }

    rows = []
    for line in USAGE_LOG.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a half-written final line must not break the report

    by_day, by_model = defaultdict(float), defaultdict(float)
    for row in rows:
        day = (row.get("at") or "")[:10]
        cost = _cost(row)
        by_day[day] += cost
        by_model[row.get("model") or "unknown"] += cost

    recent = sorted(by_day.items(), reverse=True)[:days]
    return {
        "total_usd": round(sum(by_day.values()), 4),
        "today_usd": round(by_day.get(date.today().isoformat(), 0.0), 4),
        "by_day": [{"day": d, "usd": round(v, 4)} for d, v in recent],
        "by_model": {k: round(v, 4) for k, v in sorted(by_model.items(), key=lambda kv: -kv[1])},
        "calls": len(rows),
        "caveat": "Estimates from published per-token prices, not billed amounts.",
    }


def tracked_client(api_key: str) -> anthropic.Anthropic:
    """An Anthropic client whose .messages.create() records usage on every
    call automatically. Use this everywhere anthropic.Anthropic(...) was
    constructed before — one seam covers every call site in the codebase,
    present and future, with nothing for a new call site to remember to do."""
    client = anthropic.Anthropic(api_key=api_key)
    original_create = client.messages.create

    def _tracked_create(*args, model=None, **kwargs):
        response = original_create(*args, model=model, **kwargs)
        record(model, response.usage)
        return response

    client.messages.create = _tracked_create
    return client
