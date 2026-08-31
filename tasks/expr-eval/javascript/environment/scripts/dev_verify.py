#!/usr/bin/env python3
"""Developer test harness for the expression evaluator.

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


def invoke(value):
    process = subprocess.run(
        args.command,
        input=json.dumps(value) + "\n",
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
    )
    if process.returncode != 0:
        raise AssertionError(f"exit {process.returncode}: {process.stderr[-500:]}")
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON output: {process.stdout[-500:]}") from exc


def document(sources, depth=16):
    return {
        "config": {"maxDepth": depth},
        "programs": [
            {"id": f"p{index}", "source": source}
            for index, source in enumerate(sources, start=1)
        ],
    }


def check(sources, expected, depth=16):
    """Each expectation is an int for a value or a (code, offset) pair."""
    actual = invoke(document(sources, depth))
    results = []
    failed = 0
    for index, item in enumerate(expected, start=1):
        if isinstance(item, tuple):
            failed += 1
            results.append(
                {"id": f"p{index}", "error": {"code": item[0], "at": item[1]}}
            )
        else:
            results.append({"id": f"p{index}", "value": item})
    return actual == {
        "results": results,
        "stats": {"programs": len(expected), "failed": failed},
    }


MIN64 = -(2 ** 63)
MAX64 = 2 ** 63 - 1


def regression_sum():
    actual = invoke(document(["1 + 2 + 3", "2 * 3", "7"]))
    return actual == {
        "results": [
            {"id": "p1", "value": 6},
            {"id": "p2", "value": 6},
            {"id": "p3", "value": 7},
        ],
        "stats": {"programs": 3, "failed": 0},
    }


def no_programs():
    actual = invoke(document([]))
    return actual == {"results": [], "stats": {"programs": 0, "failed": 0}}


def precedence_basics():
    return check(["2 + 3 * 4", "8 >> 1 + 1", "2 * (3 + 4)"], [14, 2, 14])


def wraparound_basics():
    return check(
        [
            "9223372036854775807 + 1",
            "4294967296 * 4294967296",
            "-9223372036854775808 - 1",
        ],
        [MIN64, 0, MAX64],
    )


def division_signs():
    return check(["-7 / 2", "-7 % 2", "7 % -2"], [-3, -1, 1])


def errors_basics():
    return check(["x", "1 +", "1 / 0"], [
        ("UNDEFINED", 0),
        ("PARSE", 3),
        ("DIVIDE_BY_ZERO", 2),
    ])


def bindings_basics():
    return check(["let x = 6; x * 7"], [42])


CASES = (
    ("regression-sum", "developer", regression_sum),
    ("no-programs", "developer", no_programs),
    ("precedence-basics", "developer", precedence_basics),
    ("wraparound-basics", "developer", wraparound_basics),
    ("division-signs", "developer", division_signs),
    ("errors-basics", "developer", errors_basics),
    ("bindings-basics", "developer", bindings_basics),
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
