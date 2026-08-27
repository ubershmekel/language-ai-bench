#!/usr/bin/env python3
"""Developer test harness for the money rollup report.

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


CURRENCIES = {"USD": 2, "JPY": 0, "EUR": 2, "BHD": 3}


def document(entries, rates=(), report="USD", currencies=None):
    return {
        "reportCurrency": report,
        "currencies": dict(CURRENCIES if currencies is None else currencies),
        "rates": list(rates),
        "entries": list(entries),
    }


def entry(account, currency, amount):
    return {"account": account, "currency": currency, "amount": amount}


def expected(pairs, currency="USD"):
    return {
        "reportCurrency": currency,
        "accounts": [
            {"account": account, "total": total} for account, total in pairs
        ],
    }


def regression_flat_accounts():
    actual = invoke(
        document([entry("cash", "USD", "12.50"), entry("bank", "USD", "0.25")])
    )
    return actual == expected([("bank", "0.25"), ("cash", "12.50")])


def ancestor_rollup():
    actual = invoke(
        document([entry("a:b", "USD", "1.10"), entry("a:c", "USD", "2.20")])
    )
    return actual == expected([("a", "3.30"), ("a:b", "1.10"), ("a:c", "2.20")])


CASES = (
    ("regression-flat-accounts", regression_flat_accounts),
    ("ancestor-rollup", ancestor_rollup),
)

results = []
for case_id, function in CASES:
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
