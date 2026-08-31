import json
import os
import sys

from parse import code_points, parse_config, parse_document, parse_rule
from redact import apply_mask, find_spans, has_overlap, keep_long_enough, merge_spans


def run(value):
    document = parse_document(value)
    config = parse_config(document["config"])
    points = code_points(document["text"])
    late = os.environ.get("LAB_SABOTAGE") == "min-length-after-merge"
    seen = set()
    stats = []
    collected = []
    for item in document["rules"]:
        rule = parse_rule(item, seen, len(points))
        seen.add(rule["id"])
        found = find_spans(rule, points)
        if not late:
            found = keep_long_enough(found, config["minLength"])
        stats.append({"id": rule["id"], "matches": len(found)})
        for start, end in found:
            collected.append((start, end, rule["id"]))
    if config["policy"] == "strict" and has_overlap([item[:2] for item in collected]):
        if os.environ.get("LAB_SABOTAGE") != "strict-allows-overlap":
            raise ValueError("overlapping spans under the strict policy")
    spans = merge_spans(collected)
    if late:
        spans = [
            span
            for span in spans
            if span["end"] - span["start"] >= config["minLength"]
        ]
    redacted = apply_mask(points, spans, config["mask"])
    covered = sum(span["end"] - span["start"] for span in spans)
    return {
        "redacted": redacted,
        "spans": spans,
        "stats": {
            "codePoints": len(points),
            "redactedCodePoints": covered,
            "rules": stats,
        },
    }


try:
    print(json.dumps(run(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
