"""'Case Files' series: deliberately CURATED, not AI-generated topic selection.

Real named companies/people carry real factual-accuracy/defamation risk if an
AI freely picks subjects and invents details. So this list lives in a plain,
Austin-editable JSON file (case_study_topics.json) — only extremely
well-documented, legally-resolved-or-non-accusatory cases go on it, and each
entry carries a hand-written facts_brief the script generator must treat as
its factual anchor rather than inventing specifics from scratch.
"""
import json
import config

TOPICS_FILE = config.ROOT / "case_study_topics.json"


def _load() -> dict:
    if not TOPICS_FILE.exists():
        return {"topics": []}
    return json.loads(TOPICS_FILE.read_text(encoding="utf-8"))


def _save(data: dict):
    TOPICS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def next_topic(exclude: set | None = None) -> dict | None:
    """Return the next 'pending' curated case as an idea dict, or None if the
    whole curated list has been covered (Austin needs to add more). `exclude`
    lets a caller skip topics already claimed earlier in the same batch,
    without writing to the file until that topic actually finishes."""
    data = _load()
    exclude = exclude or set()
    for t in data.get("topics", []):
        if t["subject"] in exclude:
            continue
        if t.get("status", "pending") == "pending":
            return {
                "topic": t["subject"],
                "hook": f"The story of how {t['subject']} really happened.",
                "angle": "A factual breakdown of what became public record and why it matters.",
                "why_now": "Evergreen case study.",
                "facts_brief": t["facts_brief"],
            }
    return None


def mark_done(subject: str, video_id: str | None):
    data = _load()
    for t in data.get("topics", []):
        if t["subject"] == subject:
            t["status"] = "done"
            t["video_id"] = video_id
            break
    _save(data)


def remaining_count() -> int:
    data = _load()
    return sum(1 for t in data.get("topics", []) if t.get("status", "pending") == "pending")
