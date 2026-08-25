#!/usr/bin/env python3
"""Language-neutral HTTP verifier for once/interval schedule variants."""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--base-url", required=True)
parser.add_argument(
    "--visibility", choices=("developer", "hidden", "all"), default="all"
)
parser.add_argument("--output")
args = parser.parse_args()
base = args.base_url.rstrip("/")


def request(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        base + path,
        data=data,
        headers={"content-type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw or b"null")


def create(schedule, name="case"):
    status, body = request("POST", "/jobs", {"name": name, "schedule": schedule})
    assert status == 201, (status, body)
    return body


def next_run(job_id, after):
    query = urllib.parse.urlencode({"after": after})
    return request("GET", f"/jobs/{job_id}/next?{query}")


def regression_once():
    status, seed = request("GET", "/jobs/1")
    if status != 200 or seed != {
        "id": "1",
        "name": "backup",
        "schedule": {"kind": "once", "at": "2030-01-01T00:00:00.000Z"},
    }:
        return False
    job = create({"kind": "once", "at": "2031-02-03T04:05:06Z"}, "once")
    before = next_run(job["id"], "2031-02-03T04:05:05Z")
    boundary = next_run(job["id"], "2031-02-03T04:05:06Z")
    return (
        job["schedule"] == {"kind": "once", "at": "2031-02-03T04:05:06.000Z"}
        and before == (200, {"nextRun": "2031-02-03T04:05:06.000Z"})
        and boundary == (200, {"nextRun": None})
    )


def interval_next():
    job = create(
        {
            "kind": "interval",
            "startAt": "2032-01-01T00:00:00Z",
            "everyMinutes": 15,
        },
        "interval",
    )
    checks = (
        ("2031-12-31T23:59:59Z", "2032-01-01T00:00:00.000Z"),
        ("2032-01-01T00:00:00Z", "2032-01-01T00:15:00.000Z"),
        ("2032-01-01T00:16:00Z", "2032-01-01T00:30:00.000Z"),
    )
    return all(
        next_run(job["id"], after) == (200, {"nextRun": expected})
        for after, expected in checks
    )


def rejects_invalid_variants():
    invalid = (
        {"kind": "once", "at": "2030-01-01T00:00:00Z", "everyMinutes": 5},
        {"kind": "interval", "startAt": "2030-01-01T00:00:00Z"},
        {"kind": "interval", "startAt": "bad", "everyMinutes": 5},
        {"kind": "interval", "startAt": "2030-01-01T00:00:00Z", "everyMinutes": 0},
        {"kind": "interval", "startAt": "2030-01-01T00:00:00Z", "everyMinutes": 1.5},
        {"kind": "later", "at": "2030-01-01T00:00:00Z"},
    )
    return all(
        request("POST", "/jobs", {"name": "bad", "schedule": value})[0] == 400
        for value in invalid
    )


def patch_switches_kind():
    job = create({"kind": "once", "at": "2030-01-01T00:00:00Z"}, "switch")
    status, changed = request(
        "PATCH",
        f"/jobs/{job['id']}",
        {
            "schedule": {
                "kind": "interval",
                "startAt": "2033-01-01T00:00:00Z",
                "everyMinutes": 60,
            }
        },
    )
    return (
        status == 200
        and changed["schedule"]
        == {
            "kind": "interval",
            "startAt": "2033-01-01T00:00:00.000Z",
            "everyMinutes": 60,
        }
        and "at" not in changed["schedule"]
        and next_run(job["id"], "2033-01-01T00:00:00Z")
        == (200, {"nextRun": "2033-01-01T01:00:00.000Z"})
    )


def invalid_patch_is_atomic():
    job = create(
        {"kind": "interval", "startAt": "2034-01-01T00:00:00Z", "everyMinutes": 10},
        "atomic",
    )
    status, _ = request(
        "PATCH",
        f"/jobs/{job['id']}",
        {"name": "corrupted", "schedule": {"kind": "once", "at": "bad"}},
    )
    get_status, unchanged = request("GET", f"/jobs/{job['id']}")
    return status == 400 and get_status == 200 and unchanged == job


def errors_are_stable():
    missing = request("GET", "/jobs/999")[0] == 404
    bad_after = next_run("1", "not-a-date")[0] == 400
    empty_patch = request("PATCH", "/jobs/1", {})[0] == 400
    extra_patch = request("PATCH", "/jobs/1", {"unknown": True})[0] == 400
    return missing and bad_after and empty_patch and extra_patch


def interval_far_future():
    job = create(
        {"kind": "interval", "startAt": "2020-01-01T00:00:00Z", "everyMinutes": 7},
        "far",
    )
    return next_run(job["id"], "2040-01-01T00:00:00Z") == (
        200,
        {"nextRun": "2040-01-01T00:01:00.000Z"},
    )


CASES = (
    ("regression-once", "developer", regression_once),
    ("interval-next", "developer", interval_next),
    ("rejects-invalid-variants", "hidden", rejects_invalid_variants),
    ("patch-switches-kind", "hidden", patch_switches_kind),
    ("invalid-patch-atomic", "hidden", invalid_patch_is_atomic),
    ("errors-stable", "hidden", errors_are_stable),
    ("interval-far-future", "hidden", interval_far_future),
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
    "passed": all(x["passed"] for x in results),
    "case_results": results,
}
text = json.dumps(report, indent=2)
print(text)
if args.output:
    with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text + "\n")
sys.exit(0 if report["passed"] else 1)
