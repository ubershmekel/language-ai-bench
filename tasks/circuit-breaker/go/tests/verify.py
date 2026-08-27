#!/usr/bin/env python3
"""Language-neutral black-box verifier for the per-target circuit breaker."""

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


def per_target_isolation():
    actual = invoke(
        document(
            [
                call(0, "alpha", "error"),
                call(1, "beta", "error"),
                call(2, "alpha", "error"),
                call(3, "beta", "ok"),
                call(4, "alpha", "ok"),
                call(5, "beta", "ok"),
            ]
        )
    )
    return decisions(actual) == [
        ("alpha", "closed", True, "failure"),
        ("beta", "closed", True, "failure"),
        ("alpha", "closed", True, "failure"),
        ("beta", "closed", True, "success"),
        ("alpha", "open", False, "rejected"),
        ("beta", "closed", True, "success"),
    ] and targets(actual) == [("alpha", "open", 2), ("beta", "closed", 0)]


def cooldown_boundary():
    calls = [call(0, "a", "error"), call(10, "a", "error")]
    calls += [call(109, "a", "ok"), call(110, "a", "ok")]
    actual = invoke(document(calls))
    return decisions(actual)[2:] == [
        ("a", "open", False, "rejected"),
        ("a", "half-open", True, "success"),
    ]


def half_open_closes():
    calls = [call(0, "a", "error"), call(0, "a", "error"), call(100, "a", "ok")]
    calls.append(call(101, "a", "error"))
    actual = invoke(document(calls))
    return decisions(actual)[2:] == [
        ("a", "half-open", True, "success"),
        ("a", "closed", True, "failure"),
    ] and targets(actual) == [("a", "closed", 1)]


def half_open_reopens():
    calls = [call(0, "a", "error"), call(0, "a", "error"), call(100, "a", "error")]
    calls += [call(150, "a", "ok"), call(200, "a", "ok")]
    actual = invoke(document(calls))
    return decisions(actual)[2:] == [
        ("a", "half-open", True, "failure"),
        ("a", "open", False, "rejected"),
        ("a", "half-open", True, "success"),
    ]


def half_open_limit():
    calls = [call(0, "a", "error"), call(0, "a", "error")]
    calls += [call(100, "a", "status", 404), call(100, "a", "status", 404)]
    calls.append(call(100, "a", "ok"))
    actual = invoke(document(calls, limit=2))
    return decisions(actual)[2:] == [
        ("a", "half-open", True, "neutral"),
        ("a", "half-open", True, "neutral"),
        ("a", "half-open", False, "rejected"),
    ]


def neutral_not_counted():
    calls = [call(at, "a", "status", 404) for at in range(5)]
    actual = invoke(document(calls))
    return all(item[3] == "neutral" for item in decisions(actual)) and targets(
        actual
    ) == [("a", "closed", 0)]


def neutral_does_not_reset():
    calls = [
        call(0, "a", "error"),
        call(1, "a", "status", 404),
        call(2, "a", "error"),
    ]
    actual = invoke(document(calls))
    return targets(actual) == [("a", "open", 2)] and decisions(actual)[1] == (
        "a",
        "closed",
        True,
        "neutral",
    )


def streak_resets():
    calls = [
        call(0, "a", "error"),
        call(1, "a", "ok"),
        call(2, "a", "error"),
        call(3, "a", "status", 500),
    ]
    actual = invoke(document(calls))
    return targets(actual) == [("a", "open", 2)] and decisions(actual)[2] == (
        "a",
        "closed",
        True,
        "failure",
    )


def target_ordering():
    names = ["b", "A", "_x", "a.1", "Z", "0"]
    actual = invoke(document([call(0, name, "ok") for name in names]))
    return [item[0] for item in targets(actual)] == sorted(names)


def rejects_invalid():
    good = document([call(0, "a", "ok")])

    def broken(mutate):
        value = json.loads(json.dumps(good))
        mutate(value)
        return value

    cases = [
        broken(lambda v: v.pop("config")),
        broken(lambda v: v.update({"extra": 1})),
        broken(lambda v: v.update({"calls": {}})),
        broken(lambda v: v["config"].pop("threshold")),
        broken(lambda v: v["config"].update({"extra": 1})),
        broken(lambda v: v["config"].update({"threshold": 0})),
        broken(lambda v: v["config"].update({"threshold": True})),
        broken(lambda v: v["config"].update({"cooldownMs": -1})),
        broken(lambda v: v["config"].update({"halfOpenLimit": 0})),
        broken(lambda v: v["config"].update({"failureStatuses": [500, 500]})),
        broken(lambda v: v["config"].update({"failureStatuses": [99]})),
        broken(lambda v: v["config"].update({"failureStatuses": 500})),
        broken(lambda v: v["calls"][0].pop("at")),
        broken(lambda v: v["calls"][0].update({"extra": 1})),
        broken(lambda v: v["calls"][0].update({"at": -1})),
        broken(lambda v: v["calls"][0].update({"at": 1.5})),
        broken(lambda v: v["calls"][0].update({"target": "bad target"})),
        broken(lambda v: v["calls"][0].update({"target": ""})),
        broken(lambda v: v["calls"][0].update({"outcome": {"kind": "nope"}})),
        broken(lambda v: v["calls"][0].update({"outcome": {"kind": "ok", "status": 1}})),
        broken(lambda v: v["calls"][0].update({"outcome": {"kind": "status"}})),
        broken(
            lambda v: v["calls"][0].update(
                {"outcome": {"kind": "status", "status": 42}}
            )
        ),
        document([call(5, "a", "ok"), call(4, "a", "ok")]),
        [1, 2, 3],
        "nope",
    ]
    return all(invoke(case, expect_success=False) for case in cases)


CASES = (
    ("regression-basic-open", "developer", regression_basic_open),
    ("empty-calls", "developer", empty_calls),
    ("per-target-isolation", "hidden", per_target_isolation),
    ("cooldown-boundary", "hidden", cooldown_boundary),
    ("half-open-closes", "hidden", half_open_closes),
    ("half-open-reopens", "hidden", half_open_reopens),
    ("half-open-limit", "hidden", half_open_limit),
    ("neutral-not-counted", "hidden", neutral_not_counted),
    ("neutral-does-not-reset", "hidden", neutral_does_not_reset),
    ("streak-resets", "hidden", streak_resets),
    ("target-ordering", "hidden", target_ordering),
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
