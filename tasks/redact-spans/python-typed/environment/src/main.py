import json
import sys
from typing import TypedDict

from parse import Span, parse_config, parse_document, parse_rule
from redact import Attributed, apply_mask, find_spans, merge_spans


class RuleStat(TypedDict):
    id: str
    matches: int


class Stats(TypedDict):
    codePoints: int
    redactedCodePoints: int
    rules: list[RuleStat]


class Result(TypedDict):
    redacted: str
    spans: list[Span]
    stats: Stats


def run(value: object) -> Result:
    document = parse_document(value)
    config = parse_config(document["config"])
    text = document["text"]
    seen: set[str] = set()
    stats: list[RuleStat] = []
    collected: list[Attributed] = []
    for item in document["rules"]:
        rule = parse_rule(item, seen, len(text))
        seen.add(rule["id"])
        found = find_spans(rule, text)
        stats.append({"id": rule["id"], "matches": len(found)})
        for start, end in found:
            collected.append((start, end, rule["id"]))
    spans = merge_spans(collected)
    redacted = apply_mask(text, spans, config["mask"])
    covered = sum(span["end"] - span["start"] for span in spans)
    return {
        "redacted": redacted,
        "spans": spans,
        "stats": {
            "codePoints": len(text),
            "redactedCodePoints": covered,
            "rules": stats,
        },
    }


try:
    print(json.dumps(run(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
