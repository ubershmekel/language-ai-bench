#!/usr/bin/env python3
"""Developer test harness for the code point redaction tool.

This harness runs only the developer-visible cases. The hidden verifier used for
grading covers the same contract more thoroughly.
"""

import argparse
import json
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument(
    "--visibility", choices=("developer", "hidden", "all"), default="developer"
)
parser.add_argument("--output")
parser.add_argument("--command", nargs=argparse.REMAINDER)
args = parser.parse_args()

if not args.command:
    parser.error("provide --command")


def invoke(value, expect_success=True):
    process = subprocess.run(
        args.command,
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


CASES = (
    ("regression-literal-mask", "developer", regression_literal_mask),
    ("no-rules", "developer", no_rules),
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
