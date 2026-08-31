#!/usr/bin/env python3
"""Language-neutral black-box verifier for the expression evaluator."""

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

MIN64 = -(2 ** 63)
MAX64 = 2 ** 63 - 1


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
        timeout=30,
    )
    if not expect_success:
        return process.returncode != 0
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


def regression_sum():
    return check(["1 + 2 + 3", "2 * 3", "7"], [6, 6, 7])


def no_programs():
    actual = invoke(document([]))
    return actual == {"results": [], "stats": {"programs": 0, "failed": 0}}


def precedence_table():
    return check(
        [
            "2 + 3 * 4",
            "1 | 2 ^ 3 & 6",
            "1 + 2 == 3",
            "8 >> 1 + 1",
            "20 - 4 - 3",
            "100 / 5 / 2",
            "1 < 2 == 1",
            "-2 * -3",
            "~1 + 1",
            "2 * (3 + 4)",
        ],
        [14, 1, 1, 2, 13, 10, 1, 6, -1, 14],
    )


def wraparound():
    return check(
        [
            "9223372036854775807 + 1",
            "-9223372036854775807 - 2",
            "4294967296 * 4294967296",
            "3037000500 * 3037000500",
            "-9223372036854775807 - 1",
        ],
        [MIN64, MAX64, 0, -9223372036709301616, MIN64],
    )


def hex_and_signed_literals():
    return check(
        [
            "0x8000000000000000",
            "0xFFFFFFFFFFFFFFFF",
            "0xff",
            "18446744073709551615",
            "9223372036854775808",
        ],
        [MIN64, -1, 255, -1, MIN64],
    )


def literal_range():
    return check(
        [
            "18446744073709551616",
            "0x10000000000000000",
            "1 + 99999999999999999999",
        ],
        [
            ("LITERAL_RANGE", 0),
            ("LITERAL_RANGE", 0),
            ("LITERAL_RANGE", 4),
        ],
    )


def division_truncation():
    return check(
        [
            "-7 / 2",
            "7 / -2",
            "-7 % 2",
            "7 % -2",
            "-9223372036854775808 / -1",
            "-9223372036854775808 % -1",
            "1 / 0",
            "1 % 0",
        ],
        [-3, -3, -1, 1, MIN64, 0, ("DIVIDE_BY_ZERO", 2), ("DIVIDE_BY_ZERO", 2)],
    )


def shift_semantics():
    return check(
        [
            "-8 >> 1",
            "-1 >> 63",
            "1 << 63",
            "3 << 62",
            "-9223372036854775808 >> 63",
            "0 << 0",
        ],
        [-4, -1, MIN64, -4611686018427387904, -1, 0],
    )


def shift_range():
    return check(
        ["1 << 64", "1 >> 64", "1 << -1", "1 << 63"],
        [
            ("SHIFT_RANGE", 2),
            ("SHIFT_RANGE", 2),
            ("SHIFT_RANGE", 2),
            MIN64,
        ],
    )


def bitwise_full_width():
    return check(
        [
            "-1 & 0xFFFFFFFFFF",
            "~0",
            "0x7FFFFFFFFFFFFFFF ^ -1",
            "1 << 40 | 1",
            "-1 ^ -1",
        ],
        [1099511627775, -1, MIN64, 1099511627777, 0],
    )


def bindings_and_shadowing():
    return check(
        [
            "let x = 1; let y = x + 1; let x = 10; x * y",
            "let x = 2; let x = x * x; x * x",
            "let _a1 = 5; _a1",
        ],
        [20, 16, 5],
    )


def undefined_name():
    return check(
        ["let x = 1; x + y", "letx", "let let = 1; 2"],
        [("UNDEFINED", 15), ("UNDEFINED", 0), ("PARSE", 4)],
    )


def depth_limit():
    return check(["((1))", "(((1)))", "((1)) + ((2))"], [1, ("DEPTH", 2), 3], depth=2)


def parse_errors():
    return check(
        [
            "1 +",
            "",
            "1 1",
            "(1",
            "1 $ 2",
            "let x 1; x",
            "12abc",
            "0x",
            "1 = 2",
        ],
        [
            ("PARSE", 3),
            ("PARSE", 0),
            ("PARSE", 2),
            ("PARSE", 2),
            ("PARSE", 2),
            ("PARSE", 6),
            ("PARSE", 2),
            ("PARSE", 0),
            ("PARSE", 2),
        ],
    )


def rejects_invalid():
    good = document(["1"])

    def broken(mutate):
        value = json.loads(json.dumps(good))
        mutate(value)
        return value

    cases = [
        broken(lambda v: v.pop("config")),
        broken(lambda v: v.update({"extra": 1})),
        broken(lambda v: v.update({"config": []})),
        broken(lambda v: v.update({"programs": {}})),
        broken(lambda v: v["config"].update({"extra": 1})),
        broken(lambda v: v["config"].update({"maxDepth": 0})),
        broken(lambda v: v["config"].update({"maxDepth": True})),
        broken(lambda v: v["config"].update({"maxDepth": 1.5})),
        broken(lambda v: v["config"].update({"maxDepth": "8"})),
        broken(lambda v: v["programs"].__setitem__(0, 5)),
        broken(lambda v: v["programs"][0].pop("source")),
        broken(lambda v: v["programs"][0].update({"extra": 1})),
        broken(lambda v: v["programs"][0].update({"id": "bad id"})),
        broken(lambda v: v["programs"][0].update({"id": ""})),
        broken(lambda v: v["programs"][0].update({"id": 5})),
        broken(lambda v: v["programs"][0].update({"source": 5})),
        broken(lambda v: v["programs"][0].update({"source": None})),
        {
            "config": {"maxDepth": 4},
            "programs": [
                {"id": "same", "source": "1"},
                {"id": "same", "source": "2"},
            ],
        },
        [1, 2, 3],
        "nope",
        4,
    ]
    return all(invoke(case, expect_success=False) for case in cases)


CASES = (
    ("regression-sum", "developer", regression_sum),
    ("no-programs", "developer", no_programs),
    ("precedence-table", "hidden", precedence_table),
    ("wraparound", "hidden", wraparound),
    ("hex-and-signed-literals", "hidden", hex_and_signed_literals),
    ("literal-range", "hidden", literal_range),
    ("division-truncation", "hidden", division_truncation),
    ("shift-semantics", "hidden", shift_semantics),
    ("shift-range", "hidden", shift_range),
    ("bitwise-full-width", "hidden", bitwise_full_width),
    ("bindings-and-shadowing", "hidden", bindings_and_shadowing),
    ("undefined-name", "hidden", undefined_name),
    ("depth-limit", "hidden", depth_limit),
    ("parse-errors", "hidden", parse_errors),
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
