import json
import sys

from parse import parse_config, parse_document, parse_rule
from redact import apply_mask, find_spans, merge_spans


def run(value):
    document = parse_document(value)
    config = parse_config(document["config"])
    text = document["text"]
    seen = set()
    stats = []
    collected = []
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
