#!/usr/bin/env python3
"""Developer test harness for the per-target circuit breaker.

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


def config(threshold=2, cooldown=100, limit=1, statuses=(500, 503)):
    return {
        "threshold": threshold,
        "cooldownMs": cooldown,
        "halfOpenLimit": limit,
        "failureStatuses": list(statuses),
    }


def document(calls, **kwargs):
    return {"config": config(**kwargs), "calls": list(calls)}


def call(at, target, kind, status=None):
    outcome = {"kind": kind} if status is None else {"kind": kind, "status": status}
    return {"at": at, "target": target, "outcome": outcome}


def decisions(actual):
    return [
        (item["target"], item["state"], item["admitted"], item["recorded"])
        for item in actual["decisions"]
    ]


def targets(actual):
    return [
        (item["target"], item["state"], item["failures"]) for item in actual["targets"]
    ]


def regression_basic_open():
    actual = invoke(
        document(
            [
                call(0, "alpha", "error"),
                call(1, "alpha", "error"),
                call(2, "alpha", "error"),
            ]
        )
    )
    return decisions(actual) == [
        ("alpha", "closed", True, "failure"),
        ("alpha", "closed", True, "failure"),
        ("alpha", "open", False, "rejected"),
    ] and targets(actual) == [("alpha", "open", 2)]


def empty_calls():
    actual = invoke(document([]))
    return actual == {"decisions": [], "targets": []}


CASES = (
    ("regression-basic-open", "developer", regression_basic_open),
    ("empty-calls", "developer", empty_calls),
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
