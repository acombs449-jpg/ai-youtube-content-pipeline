"""Shared tolerant JSON extraction for LLM responses — strips code fences,
survives leading/trailing prose, tolerates a leading 'json' label, and repairs
the two defects the script model actually emits.

WHY THE REPAIR PASS EXISTS
--------------------------
2026-08-08: FinanceYT-WeeklyLong died with
    Expecting ',' delimiter: line 2 column 2212 (char 2213)
The long-form narration is ~2-3k characters of prose about things like
    What "Minimum Payment" Actually Covers
and the model had left one of those inner double quotes unescaped. json.loads
closes the string early and then demands a comma. One stray quote in a 2000-word
narration threw away the entire weekly video — the run was single-shot with no
repair and no retry, so nothing published that week.

Raw newlines inside a string value fail the same way (json.loads rejects literal
control characters in strings), and the model emits those too when it formats
narration into paragraphs.

Both are mechanical to fix without guessing at meaning, so `extract_json` now
tries strict parsing first and only falls back to repair. Callers that need a
second opinion should still retry the model — see scriptgen.write_script.
"""
import json

# Characters that legitimately follow a string's closing quote in valid JSON.
_AFTER_STRING = {",", ":", "}", "]"}
_ESCAPES = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}


def _repair(text: str) -> str:
    """Escape unescaped quotes and raw control chars inside JSON string values.

    Walks the text tracking string state. A quote inside a string is treated as
    the closing quote only if the next non-whitespace character is structural
    (`,` `:` `}` `]`) or end-of-input; otherwise it is inner prose and gets
    escaped. Structure outside strings is never touched, so this cannot turn
    malformed JSON into *differently* malformed JSON — it either fixes the
    string bodies or leaves the original error to surface.
    """
    out = []
    in_string = False
    escaped = False

    for i, ch in enumerate(text):
        if not in_string:
            out.append(ch)
            if ch == '"':
                in_string = True
            continue

        # Inside a string.
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if ch == "\\":
            out.append(ch)
            escaped = True
            continue
        if ch in _ESCAPES:
            out.append(_ESCAPES[ch])
            continue
        if ch == '"':
            nxt = next((c for c in text[i + 1:] if not c.isspace()), "")
            if nxt in _AFTER_STRING or nxt == "":
                out.append(ch)
                in_string = False
            else:
                out.append('\\"')       # inner prose quote — escape it
            continue
        out.append(ch)

    return "".join(out)


def extract_json(text: str):
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1]
    text = text.strip()
    if text[:4].lower() == "json":
        text = text[4:].strip()
    if not text.startswith(("{", "[")):
        starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
        if starts:
            text = text[min(starts):]
    end = max(text.rfind("}"), text.rfind("]"))
    if end != -1:
        text = text[:end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Repair pass. If this also fails, raise the ORIGINAL-shaped error from
        # the repaired text so the log still points at a real column.
        return json.loads(_repair(text))


def text_of(message) -> str:
    """The model's text, regardless of what other content-block types
    surround it.

    2026-09-06: research.get_ideas crashed with 'ThinkingBlock' object has no
    attribute 'text' from a bare `message.content[0].text` — the account
    started returning a leading thinking block before the text block, so
    index 0 was no longer safe to assume. Scanning for the text block instead
    of trusting position handles a thinking block, or any other future
    leading block type, the same way.
    """
    return next(b.text for b in message.content if b.type == "text")


def parse_or_retry(client, *, model, max_tokens, system, messages, label,
                    **extra):
    """Parse the model's JSON, re-prompting ONCE if it comes back unparseable.

    extract_json already repairs unescaped quotes and raw newlines, so
    reaching the retry means the response was broken in some other way
    (usually truncated at max_tokens). One extra call is far cheaper than
    losing the whole video: on 2026-08-08 a single bad character cost the
    entire weekly long-form upload, because that call site was a one-shot
    parse with no fallback (see the module docstring). Moved here from
    scriptgen.py 2026-09-06 so research.py's ideas call gets the same
    protection instead of a second, less-defended copy of the same logic.

    extra is passed straight through to messages.create — e.g. research.py's
    schema-constrained ideas call needs output_config, which scriptgen.py's
    script call does not.
    """
    # thinking defaults to disabled: every caller here wants one exact JSON
    # shape back, nothing benefits from extended reasoning, and 2026-09-06
    # proved the cost of leaving it on an unstated default — a 500-max_tokens
    # concept call (scriptgen._concept) came back truncated after only ~115
    # characters of real JSON because the account spent the rest of the
    # budget on an unrequested thinking block. A caller that genuinely wants
    # thinking can still override it through **extra.
    create_kwargs = {"thinking": {"type": "disabled"}, **extra}
    msg = client.messages.create(model=model, max_tokens=max_tokens,
                                 system=system, messages=messages, **create_kwargs)
    text = text_of(msg)
    try:
        return extract_json(text)
    except (json.JSONDecodeError, ValueError, IndexError) as exc:
        print(f"     ! {label}: unparseable JSON ({exc}); retrying once")

    retry_messages = list(messages) + [
        {"role": "assistant", "content": text},
        {"role": "user", "content":
            "That response was not valid JSON and could not be parsed. Send the "
            "SAME content again as a single valid JSON object and nothing else: "
            "no prose, no code fence. Escape every double quote inside a string "
            "as \\\" and every line break as \\n."},
    ]
    msg = client.messages.create(model=model, max_tokens=max_tokens,
                                 system=system, messages=retry_messages, **create_kwargs)
    return extract_json(text_of(msg))
