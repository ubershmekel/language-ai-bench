#!/usr/bin/env python3
"""Extract reproducible workflow-quality signals from private Pier ATIF artifacts."""

from __future__ import annotations

import argparse
import json
import pathlib
import re

VERIFY = re.compile(r"(?:^|[\s;&|])(?:\./)?scripts/verify-local(?:\s|$)")
STATIC_CHECK = re.compile(r"(?:tsc(?:\s|$)|go\s+(?:test|vet|build)(?:\s|$)|python\s+-m\s+(?:mypy|pyright)|npm\s+(?:run\s+)?(?:lint|typecheck))")
EDIT = re.compile(r"(?:sed\s+-i|cat\s+.*>|tee\s+|apply_patch|perl\s+-.*-i)")
SUBMIT = "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"


def commands(trajectory: dict) -> list[dict]:
    extracted = []
    for step in trajectory.get("steps", []):
        if step.get("source") != "agent":
            continue
        calls = step.get("tool_calls") or []
        results = ((step.get("observation") or {}).get("results") or [])
        for index, call in enumerate(calls):
            command = (call.get("arguments") or {}).get("command")
            if not isinstance(command, str):
                continue
            result = results[index] if index < len(results) else {}
            content = result.get("content", result)
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    content = {}
            extracted.append({
                "step_id": step.get("step_id"),
                "command": command,
                "returncode": content.get("returncode") if isinstance(content, dict) else None,
            })
    return extracted


def extract(trajectory: dict, result: dict | None = None) -> dict:
    actions = commands(trajectory)
    verifications = [action for action in actions if VERIFY.search(action["command"])]
    submits = [i for i, action in enumerate(actions) if action["command"].strip() == SUBMIT]
    first_submit = submits[0] if submits else None
    prior = ([action for i, action in enumerate(actions) if i < first_submit and VERIFY.search(action["command"])] if first_submit is not None else [])
    malformed = sum(1 for step in trajectory.get("steps", []) if step.get("source") == "agent" and not (step.get("tool_calls") or []))
    hidden_pass = None
    cost = None
    if result:
        hidden_pass = result.get("verifier_result", {}).get("rewards", {}).get("reward") == 1.0
        cost = result.get("agent_result", {}).get("cost_usd")
    return {
        "schema_version": "1.0.0",
        "hidden_test_pass": hidden_pass,
        "first_developer_verification_pass": verifications[0]["returncode"] == 0 if verifications else None,
        "developer_verification_before_submit": bool(prior),
        "passing_developer_verification_before_submit": any(action["returncode"] == 0 for action in prior),
        "verification_attempts": len(verifications),
        "static_check_invocations": sum(bool(STATIC_CHECK.search(action["command"])) for action in actions),
        "edit_command_invocations": sum(bool(EDIT.search(action["command"])) for action in actions),
        "malformed_actions": malformed,
        "submitted": first_submit is not None,
        "command_count": len(actions),
        "cost_usd": cost,
        "patch_statistics": {
            "files_changed": None,
            "lines_added": None,
            "lines_deleted": None,
            "dependency_manifest_changed": None,
            "reason": "final workspace artifact was not retained by this Pier task",
        },
        "review_findings": None,
    }


def find_trial(job: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    candidates = list(job.glob("*/agent/trajectory.json"))
    if len(candidates) != 1:
        raise SystemExit(f"expected exactly one trial trajectory under {job}; found {len(candidates)}")
    trajectory = candidates[0]
    result = trajectory.parents[1] / "result.json"
    if not result.is_file():
        raise SystemExit(f"missing trial result: {result}")
    return trajectory, result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jobs", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args()
    receipts = []
    for raw in args.jobs:
        trajectory_path, result_path = find_trial(pathlib.Path(raw))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        receipt = extract(json.loads(trajectory_path.read_text(encoding="utf-8")), result)
        receipt["task_name"] = result.get("task_name")
        receipt["task_checksum"] = result.get("task_checksum")
        receipts.append(receipt)
    text = json.dumps({"schema_version": "1.0.0", "runs": receipts}, indent=2) + "\n"
    if args.output:
        output = pathlib.Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
