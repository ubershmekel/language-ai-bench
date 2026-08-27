#!/usr/bin/env python3
"""Language-neutral black-box verifier for layered configuration merging."""

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
        timeout=15,
    )
    if not expect_success:
        return process.returncode != 0
    if process.returncode != 0:
        raise AssertionError(f"exit {process.returncode}: {process.stderr[-500:]}")
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON output: {process.stdout[-500:]}") from exc


def envelope(defaults=None, file=None, env=None, cli=None):
    return {
        "defaults": {} if defaults is None else defaults,
        "file": {} if file is None else file,
        "env": {} if env is None else env,
        "cli": {} if cli is None else cli,
    }


def regression_flat():
    actual = invoke(
        envelope({"host": "localhost", "port": 80}, {"port": 8080}, cli={"debug": True})
    )
    return actual == {"host": "localhost", "port": 8080, "debug": True}


def nested_precedence():
    actual = invoke(
        envelope(
            {"db": {"host": "db", "port": 5432, "pool": {"min": 1, "max": 5}}},
            {"db": {"port": 6432, "pool": {"max": 10}}},
            {"db": {"pool": {"min": 2}}},
            {"db": {"ssl": True}},
        )
    )
    return actual == {
        "db": {
            "host": "db",
            "port": 6432,
            "pool": {"min": 2, "max": 10},
            "ssl": True,
        }
    }


def deletes_nested_leaf():
    actual = invoke(
        envelope(
            {"db": {"host": "db", "password": "secret"}}, {"db": {"password": None}}
        )
    )
    return actual == {"db": {"host": "db"}}


def deletes_whole_object():
    actual = invoke(
        envelope(
            {"cache": {"host": "cache", "ttl": 30}, "keep": 1}, env={"cache": None}
        )
    )
    return actual == {"keep": 1}


def delete_then_readd():
    actual = invoke(
        envelope(
            {"features": {"alpha": 1, "beta": 2}},
            {"features": {"alpha": None}},
            {"features": {"alpha": 9, "gamma": 3}},
        )
    )
    return actual == {"features": {"alpha": 9, "beta": 2, "gamma": 3}}


def arrays_replace():
    actual = invoke(
        envelope(
            {"ports": [80, 443], "nested": {"tags": ["a"]}},
            {"ports": [8080]},
            cli={"nested": {"tags": ["b", "c"]}},
        )
    )
    return actual == {"ports": [8080], "nested": {"tags": ["b", "c"]}}


def type_transitions():
    actual = invoke(
        envelope(
            {"value": 1, "other": {"x": 1}},
            {"value": {"x": 2}, "other": "flat"},
            env={"value": {"y": 3}},
        )
    )
    return actual == {"value": {"x": 2, "y": 3}, "other": "flat"}


def rejects_invalid():
    invalid = [
        [],
        {"defaults": {}, "file": {}, "env": {}},
        {"defaults": {}, "file": {}, "env": {}, "cli": {}, "extra": {}},
        {"defaults": {}, "file": [], "env": {}, "cli": {}},
        {"defaults": None, "file": {}, "env": {}, "cli": {}},
    ]
    return all(invoke(value, expect_success=False) for value in invalid)


CASES = (
    ("regression-flat", "developer", regression_flat),
    ("nested-precedence", "developer", nested_precedence),
    ("deletes-nested-leaf", "hidden", deletes_nested_leaf),
    ("deletes-whole-object", "hidden", deletes_whole_object),
    ("delete-then-readd", "hidden", delete_then_readd),
    ("arrays-replace", "hidden", arrays_replace),
    ("type-transitions", "hidden", type_transitions),
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

report = {
    "schema_version": "1.0.0",
    "passed": all(item["passed"] for item in results),
    "case_results": results,
}
rendered = json.dumps(report, indent=2)
print(rendered)
if args.output:
    with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered + "\n")
sys.exit(0 if report["passed"] else 1)
