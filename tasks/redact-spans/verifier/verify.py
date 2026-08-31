#!/usr/bin/env python3
"""Language-neutral black-box verifier for the code point redaction tool."""

import argparse
import json
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument(
    "--visibility", choices=("developer", "hidden", "all"), default="all"
)
parser.add_argument("--output")
parser.add_argument("--docker-image")
parser.add_argument("--sabotage")
parser.add_argument("--command", nargs=argparse.REMAINDER)
args = parser.parse_args()

if bool(args.docker_image) == bool(args.command):
    parser.error("provide exactly one of --docker-image or --command")

GRIN = "\U0001f600"
PARTY = "\U0001f389"
LOCK = "\U0001f512"


def invoke(value, expect_success=True):
    if args.docker_image:
        command = ["docker", "run", "--rm", "-i"]
        if args.sabotage:
            command += ["-e", f"LAB_SABOTAGE={args.sabotage}"]
        command.append(args.docker_image)
    else:
        command = args.command
    process = subprocess.run(
        command,
        input=json.dumps(value) + "\n",
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=20,
    )
    if not expect_success:
        return process.returncode != 0
    if process.returncode != 0:
        raise AssertionError(f"exit {process.returncode}: {process.stderr[-500:]}")
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON output: {process.stdout[-500:]}") from exc


def document(text, rules, mask="*", policy="merge", minimum=1):
    return {
        "config": {"mask": mask, "policy": policy, "minLength": minimum},
        "text": text,
        "rules": list(rules),
    }


def literal(identifier, value):
    return {"id": identifier, "kind": "literal", "value": value}


def span(identifier, start, end):
    return {"id": identifier, "kind": "span", "start": start, "end": end}


def expect(redacted, spans, rules):
    covered = sum(end - start for start, end, _ in spans)
    return {
        "redacted": redacted,
        "spans": [
            {"start": start, "end": end, "rules": list(ids)}
            for start, end, ids in spans
        ],
        "stats": {
            "codePoints": len(redacted),
            "redactedCodePoints": covered,
            "rules": [
                {"id": identifier, "matches": count} for identifier, count in rules
            ],
        },
    }


def regression_literal_mask():
    actual = invoke(document("token abc secret abc end", [literal("r1", "abc")]))
    return actual == expect(
        "token *** secret *** end",
        [(6, 9, ["r1"]), (17, 20, ["r1"])],
        [("r1", 2)],
    )


def no_rules():
    actual = invoke(document("hello", []))
    return actual == expect("hello", [], [])


def code_point_offsets():
    text = f"a{GRIN}b{PARTY}c"
    actual = invoke(document(text, [span("r1", 1, 4)]))
    return actual == expect("a***c", [(1, 4, ["r1"])], [("r1", 1)])


def astral_mask():
    text = f"{GRIN}abcdef{GRIN}"
    actual = invoke(
        document(text, [literal("r1", "abc"), literal("r2", "def")], mask=LOCK)
    )
    return actual == expect(
        GRIN + LOCK * 6 + GRIN,
        [(1, 7, ["r1", "r2"])],
        [("r1", 1), ("r2", 1)],
    )


def literal_non_overlapping():
    actual = invoke(document("aaaaa", [literal("r1", "aaa")]))
    return actual == expect("***aa", [(0, 3, ["r1"])], [("r1", 1)])


def astral_literal_scan():
    text = GRIN * 5
    actual = invoke(document(text, [literal("r1", GRIN * 3)]))
    return actual == expect("***" + GRIN * 2, [(0, 3, ["r1"])], [("r1", 1)])


def merge_touching():
    text = f"{GRIN}bc{PARTY}ef"
    actual = invoke(document(text, [span("r1", 0, 3), span("r2", 3, 6)]))
    return actual == expect(
        "******", [(0, 6, ["r1", "r2"])], [("r1", 1), ("r2", 1)]
    )


def merge_overlapping():
    rules = [span("r1", 0, 4), span("r2", 2, 7), span("r3", 8, 10)]
    actual = invoke(document("0123456789", rules))
    return actual == expect(
        "*******7**",
        [(0, 7, ["r1", "r2"]), (8, 10, ["r3"])],
        [("r1", 1), ("r2", 1), ("r3", 1)],
    )


def min_length_drops_before_merge():
    text = f"{GRIN}1234{PARTY}6789"
    rules = [span("r1", 0, 2), span("r2", 2, 5), literal("r3", "89")]
    actual = invoke(document(text, rules, minimum=3))
    return actual == expect(
        f"{GRIN}1***{PARTY}6789",
        [(2, 5, ["r2"])],
        [("r1", 0), ("r2", 1), ("r3", 0)],
    )


def strict_rejects_overlap():
    rules = [span("r1", 0, 4), span("r2", 2, 7)]
    rejected = invoke(document("0123456789", rules, policy="strict"), False)
    merged = invoke(document("0123456789", rules))
    return rejected and merged == expect(
        "*******789", [(0, 7, ["r1", "r2"])], [("r1", 1), ("r2", 1)]
    )


def strict_allows_touching():
    rules = [span("r1", 0, 3), span("r2", 3, 6)]
    actual = invoke(document("abcdef", rules, policy="strict"))
    return actual == expect(
        "******", [(0, 6, ["r1", "r2"])], [("r1", 1), ("r2", 1)]
    )


def stats_and_order():
    text = f"cat dog cat {GRIN} dog"
    rules = [
        literal("m", "dog"),
        literal("a", "cat"),
        span("z", 2, 5),
        literal("b", "zzz"),
    ]
    actual = invoke(document(text, rules))
    return actual == expect(
        f"******* *** {GRIN} ***",
        [(0, 7, ["a", "m", "z"]), (8, 11, ["a"]), (14, 17, ["m"])],
        [("m", 2), ("a", 2), ("z", 1), ("b", 0)],
    )


def rejects_invalid():
    good = document("abc", [literal("r1", "a")])

    def broken(mutate):
        value = json.loads(json.dumps(good))
        mutate(value)
        return value

    cases = [
        broken(lambda v: v.pop("config")),
        broken(lambda v: v.update({"extra": 1})),
        broken(lambda v: v.update({"text": 5})),
        broken(lambda v: v.update({"rules": {}})),
        broken(lambda v: v.update({"config": []})),
        broken(lambda v: v["config"].pop("mask")),
        broken(lambda v: v["config"].update({"extra": 1})),
        broken(lambda v: v["config"].update({"mask": ""})),
        broken(lambda v: v["config"].update({"mask": "ab"})),
        broken(lambda v: v["config"].update({"mask": 5})),
        broken(lambda v: v["config"].update({"policy": "nope"})),
        broken(lambda v: v["config"].update({"minLength": 0})),
        broken(lambda v: v["config"].update({"minLength": True})),
        broken(lambda v: v["config"].update({"minLength": 1.5})),
        broken(lambda v: v["rules"].__setitem__(0, 5)),
        broken(lambda v: v["rules"][0].update({"kind": "nope"})),
        broken(lambda v: v["rules"][0].pop("value")),
        broken(lambda v: v["rules"][0].update({"extra": 1})),
        broken(lambda v: v["rules"][0].update({"id": "bad id"})),
        broken(lambda v: v["rules"][0].update({"id": ""})),
        broken(lambda v: v["rules"][0].update({"id": 5})),
        broken(lambda v: v["rules"][0].update({"value": ""})),
        broken(lambda v: v["rules"][0].update({"value": 5})),
        document("abc", [literal("r1", "a"), literal("r1", "b")]),
        document("abc", [span("r1", -1, 2)]),
        document("abc", [span("r1", 3, 3)]),
        document("abc", [span("r1", 2, 1)]),
        document("abc", [span("r1", 0, 4)]),
        document("abc", [span("r1", 1.5, 2)]),
        document("abc", [span("r1", 0, True)]),
        document(f"a{GRIN}c", [span("r1", 0, 4)]),
        document("0123456789", [span("r1", 0, 4), span("r2", 2, 7)], policy="strict"),
        [1, 2, 3],
        "nope",
    ]
    return all(invoke(case, expect_success=False) for case in cases)


CASES = (
    ("regression-literal-mask", "developer", regression_literal_mask),
    ("no-rules", "developer", no_rules),
    ("code-point-offsets", "hidden", code_point_offsets),
    ("astral-mask", "hidden", astral_mask),
    ("literal-non-overlapping", "hidden", literal_non_overlapping),
    ("astral-literal-scan", "hidden", astral_literal_scan),
    ("merge-touching", "hidden", merge_touching),
    ("merge-overlapping", "hidden", merge_overlapping),
    ("min-length-drops-before-merge", "hidden", min_length_drops_before_merge),
    ("strict-rejects-overlap", "hidden", strict_rejects_overlap),
    ("strict-allows-touching", "hidden", strict_allows_touching),
    ("stats-and-order", "hidden", stats_and_order),
    ("rejects-invalid", "hidden", rejects_invalid),
)

results = []
for case_id, visibility, function in CASES:
    if args.visibility not in ("all", visibility):
        continue
    started = time.monotonic()
    try:
        passed = bool(function())
        error = None
    except Exception as exc:
        passed = False
        error = f"{type(exc).__name__}: {exc}"
    result = {
        "case_id": case_id,
        "passed": passed,
        "duration_ms": round((time.monotonic() - started) * 1000, 2),
    }
    if error:
        result["error"] = error
    results.append(result)

report_document = {
    "schema_version": "1.0.0",
    "passed": all(item["passed"] for item in results),
    "case_results": results,
}
rendered = json.dumps(report_document, indent=2)
print(rendered)
if args.output:
    with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered + "\n")
sys.exit(0 if report_document["passed"] else 1)
