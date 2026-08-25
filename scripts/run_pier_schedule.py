#!/usr/bin/env python3
"""Run a planned Pier study serially with measured-cost and artifact gates."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes((json.dumps(value, indent=2) + "\n").encode("utf-8"))
    temporary.replace(path)


def trial_results(root: pathlib.Path) -> dict[pathlib.Path, dict[str, Any]]:
    results = {}
    if not root.exists():
        return results
    for path in root.rglob("result.json"):
        try:
            value = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if "agent_result" in value:
            results[path] = value
    return results


def display_path(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def measured_trial(path: pathlib.Path, value: dict[str, Any]) -> dict[str, Any]:
    agent = value.get("agent_result") or {}
    cost = agent.get("cost_usd")
    if not isinstance(cost, (int, float)) or cost < 0:
        raise RuntimeError(f"missing measured cost in {path}")
    exception = value.get("exception_info")
    verifier = value.get("verifier_result") or {}
    reward = (verifier.get("rewards") or {}).get("reward")
    artifact = path.parent / "artifacts" / "workspace"
    return {
        "result_path": display_path(path),
        "cost_usd": float(cost),
        "exception_type": exception.get("exception_type") if exception else None,
        "reward": reward,
        "workspace_artifact": display_path(artifact),
        "workspace_artifact_captured": artifact.exists(),
    }


def pier_executable() -> str:
    windows = ROOT / ".venv" / "Scripts" / "pier.exe"
    return str(windows) if windows.exists() else "pier"


def command_for(
    row: dict[str, Any], study: dict[str, Any], jobs_dir: pathlib.Path
) -> list[str]:
    settings = study["model_settings"]
    return [
        pier_executable(),
        "run",
        "-p",
        str(ROOT / row["task_path"]),
        "--agent",
        "mini-swe-agent",
        "--model",
        study["model"],
        "--env-file",
        str(ROOT / ".env"),
        "--agent-kwarg",
        f"reasoning_effort={settings['reasoning_effort']}",
        "--agent-kwarg",
        f"set_cache_control={settings['cache_control']}",
        "--n-attempts",
        "1",
        "--n-concurrent",
        "1",
        "--max-retries",
        "0",
        "--sample-seed",
        str(row["sample_seed"]),
        "--artifact",
        "/workspace",
        "--jobs-dir",
        str(jobs_dir),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=pathlib.Path, default=ROOT / "study_v0.6.json")
    parser.add_argument(
        "--schedule", type=pathlib.Path, default=ROOT / "study_v0.6_schedule.json"
    )
    parser.add_argument(
        "--jobs-dir",
        type=pathlib.Path,
        default=ROOT / "jobs" / "v06-clean-polyglot",
    )
    parser.add_argument(
        "--ledger",
        type=pathlib.Path,
        default=ROOT / ".benchmark-state" / "v06-spend.json",
    )
    parser.add_argument("--max-spend-usd", type=float, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    study = read_json(args.study)
    receipt = read_json(args.schedule)
    if not receipt.get("launch_ready"):
        raise SystemExit("schedule receipt is not launch-ready")
    if receipt["study_id"] != study["study_id"]:
        raise SystemExit("study and schedule IDs differ")
    if args.max_spend_usd > study["study_cost_limit_usd"]:
        raise SystemExit("requested ceiling exceeds the committed study limit")

    ledger = (
        read_json(args.ledger)
        if args.ledger.exists()
        else {
            "schema_version": "1.0.0",
            "study_id": study["study_id"],
            "spent_usd": 0.0,
            "runs": [],
        }
    )
    completed = {item["order_index"] for item in ledger["runs"]}
    pending = [
        row for row in receipt["schedule"] if row["order_index"] not in completed
    ]
    print(
        f"study={study['study_id']} pending={len(pending)} "
        f"spent_usd={ledger['spent_usd']:.6f} ceiling_usd={args.max_spend_usd:.2f}"
    )
    if args.dry_run:
        for row in pending:
            print(
                f"{row['order_index']:02d} {row['task_family']} "
                f"{row['language']} attempt={row['attempt']} "
                f"seed={row['sample_seed']}"
            )
        return 0

    if not (ROOT / ".env").is_file():
        raise SystemExit("missing ignored .env")
    for row in pending:
        if ledger["spent_usd"] >= args.max_spend_usd:
            raise SystemExit("study spend ceiling reached")
        rollout_dir = args.jobs_dir / (
            f"{row['order_index']:02d}-{row['task_family']}-"
            f"{row['language']}-a{row['attempt']}"
        )
        before = set(trial_results(rollout_dir))
        process = subprocess.run(command_for(row, study, rollout_dir), cwd=ROOT)
        after = trial_results(rollout_dir)
        created = sorted(set(after) - before)
        if len(created) != 1:
            raise SystemExit(
                f"expected one new trial result for order {row['order_index']}, "
                f"found {len(created)}"
            )
        measurement = measured_trial(created[0], after[created[0]])
        entry = {**row, **measurement, "pier_exit_status": process.returncode}
        ledger["runs"].append(entry)
        ledger["spent_usd"] = round(
            sum(item["cost_usd"] for item in ledger["runs"]), 10
        )
        write_json(args.ledger, ledger)
        print(
            f"{row['order_index']:02d} {row['language']} "
            f"reward={measurement['reward']} "
            f"cost_usd={measurement['cost_usd']:.6f} "
            f"total_usd={ledger['spent_usd']:.6f}"
        )
        if measurement["cost_usd"] > study["per_rollout_cost_limit_usd"]:
            raise SystemExit("per-rollout cost limit exceeded")
        if ledger["spent_usd"] > args.max_spend_usd:
            raise SystemExit("study spend ceiling crossed")
        if measurement["exception_type"]:
            raise SystemExit(
                f"Pier exception: {measurement['exception_type']} "
                f"(order {row['order_index']})"
            )
        if not measurement["workspace_artifact_captured"]:
            raise SystemExit(
                f"workspace artifact missing for order {row['order_index']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
