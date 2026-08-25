#!/usr/bin/env python3
"""Language-neutral black-box verifier for exact money rollup reporting."""

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


def rate(source, target, value):
    return {"from": source, "to": target, "rate": value}


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


def chained_conversion():
    actual = invoke(
        document(
            [entry("ops:tokyo", "JPY", "1000")],
            [rate("JPY", "EUR", "0.0061"), rate("EUR", "USD", "1.0842")],
        )
    )
    return actual == expected([("ops", "6.61"), ("ops:tokyo", "6.61")])


def shortest_path_preferred():
    actual = invoke(
        document(
            [entry("ops", "JPY", "1000")],
            [
                rate("JPY", "USD", "0.0067"),
                rate("JPY", "EUR", "0.0061"),
                rate("EUR", "USD", "1.0842"),
            ],
        )
    )
    return actual == expected([("ops", "6.70")])


def half_even_ties():
    actual = invoke(
        document(
            [
                entry("t:a", "BHD", "0.125"),
                entry("t:b", "BHD", "0.135"),
                entry("t:c", "BHD", "-0.125"),
                entry("t:d", "BHD", "-0.135"),
            ],
            [rate("BHD", "USD", "1")],
        )
    )
    return actual == expected(
        [
            ("t", "0.00"),
            ("t:a", "0.12"),
            ("t:b", "0.14"),
            ("t:c", "-0.12"),
            ("t:d", "-0.14"),
        ]
    )


def per_entry_rounding():
    actual = invoke(
        document(
            [entry("s:x", "BHD", "0.004"), entry("s:y", "BHD", "0.004")],
            [rate("BHD", "USD", "1")],
        )
    )
    return actual == expected([("s", "0.00"), ("s:x", "0.00"), ("s:y", "0.00")])


def exact_large_magnitude():
    actual = invoke(
        document(
            [entry("v", "JPY", "123456789012345678")],
            [rate("JPY", "USD", "0.01")],
        )
    )
    return actual == expected([("v", "1234567890123456.78")])


def zero_and_negative_formatting():
    actual = invoke(
        document(
            [
                entry("n:p", "USD", "10.00"),
                entry("n:q", "USD", "-10.00"),
                entry("m", "USD", "-0.40"),
            ],
            [rate("USD", "JPY", "1")],
            report="JPY",
        )
    )
    return actual == expected(
        [("m", "0"), ("n", "0"), ("n:p", "10"), ("n:q", "-10")], "JPY"
    )


def prefix_sorting():
    actual = invoke(
        document(
            [
                entry("a:b:c", "USD", "1.00"),
                entry("a:bb", "USD", "2.00"),
                entry("a_b", "USD", "5.00"),
                entry("A:z", "USD", "4.00"),
            ]
        )
    )
    return actual == expected(
        [
            ("A", "4.00"),
            ("A:z", "4.00"),
            ("a", "3.00"),
            ("a:b", "1.00"),
            ("a:b:c", "1.00"),
            ("a:bb", "2.00"),
            ("a_b", "5.00"),
        ]
    )


def rejects_bad_paths():
    ambiguous = document(
        [entry("x", "JPY", "100")],
        [
            rate("JPY", "EUR", "2"),
            rate("JPY", "BHD", "3"),
            rate("EUR", "USD", "1"),
            rate("BHD", "USD", "1"),
        ],
    )
    missing = document([entry("x", "JPY", "100")], [rate("EUR", "USD", "1")])
    reversed_only = document([entry("x", "JPY", "100")], [rate("USD", "JPY", "0.01")])
    return all(
        invoke(value, expect_success=False)
        for value in (ambiguous, missing, reversed_only)
    )


def empty_entries():
    actual = invoke(document([]))
    return actual == expected([])


def rejects_invalid():
    invalid = [
        [],
        "text",
        {"currencies": {"USD": 2}, "rates": [], "entries": []},
        {**document([]), "extra": 1},
        document([entry("cash", "USD", "1.005")]),
        document([entry("cash", "USD", "+1.00")]),
        document([entry("cash", "USD", "1.")]),
        document([entry("cash", "USD", ".50")]),
        document([entry("cash", "USD", "1,50")]),
        document([entry("cash", "USD", 100)]),
        document([entry("cash", "CHF", "1.00")]),
        document([entry("", "USD", "1.00")]),
        document([entry("a::b", "USD", "1.00")]),
        document([entry("a:", "USD", "1.00")]),
        document([entry("a b", "USD", "1.00")]),
        document([{"account": "cash", "currency": "USD"}]),
        document([{**entry("cash", "USD", "1.00"), "note": "x"}]),
        document([], [rate("JPY", "USD", "0.01"), rate("JPY", "USD", "0.02")]),
        document([], [rate("USD", "USD", "1")]),
        document([], [rate("JPY", "USD", "0")]),
        document([], [rate("JPY", "USD", "-1")]),
        document([], [rate("JPY", "USD", "0.000000001")]),
        document([], [rate("JPY", "CHF", "1")]),
        document([], [{"from": "JPY", "to": "USD"}]),
        document([], report="CHF"),
        document([], currencies={"USD": 5}),
        document([], currencies={"USD": -1}),
        document([], currencies={"USD": True}),
        document([], currencies={"USD": 2.5}),
        document([], currencies={}),
        {**document([]), "rates": {}},
        {**document([]), "entries": {}},
    ]
    return all(invoke(value, expect_success=False) for value in invalid)


CASES = (
    ("regression-flat-accounts", "developer", regression_flat_accounts),
    ("ancestor-rollup", "developer", ancestor_rollup),
    ("chained-conversion", "hidden", chained_conversion),
    ("shortest-path-preferred", "hidden", shortest_path_preferred),
    ("half-even-ties", "hidden", half_even_ties),
    ("per-entry-rounding", "hidden", per_entry_rounding),
    ("exact-large-magnitude", "hidden", exact_large_magnitude),
    ("zero-and-negative-formatting", "hidden", zero_and_negative_formatting),
    ("prefix-sorting", "hidden", prefix_sorting),
    ("rejects-bad-paths", "hidden", rejects_bad_paths),
    ("empty-entries", "hidden", empty_entries),
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
