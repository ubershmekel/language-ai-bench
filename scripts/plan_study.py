#!/usr/bin/env python3
"""Validate a prospective study and create a deterministic blocked schedule."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def validate(study: dict, require_launch_ready: bool = False) -> list[str]:
    errors: list[str] = []
    languages = study.get("languages", [])
    # Arms are no longer one-per-language: python and python-typed are the
    # within-language contrast, so the count is open and only uniqueness binds.
    if len(languages) < 2 or len(set(languages)) != len(languages):
        errors.append("languages must contain at least two unique values")
    if study.get("attempts_per_cell", 0) < 1:
        errors.append("attempts_per_cell must be positive")
    if study.get("per_rollout_cost_limit_usd", 0) <= 0:
        errors.append("per_rollout_cost_limit_usd must be positive")
    if study.get("study_cost_limit_usd", 0) <= 0:
        errors.append("study_cost_limit_usd must be positive")

    ready = [family for family in study.get("task_families", []) if family["status"] == "ready"]
    for family in ready:
        paths = family.get("paths", {})
        missing = sorted(set(languages) - set(paths))
        if missing:
            errors.append(f"{family['id']}: ready family missing {', '.join(missing)}")
        for language, relative in paths.items():
            task_path = ROOT / relative
            if not task_path.is_dir() or not (task_path / "task.toml").is_file():
                errors.append(f"{family['id']}/{language}: invalid task path {relative}")

    projected = (
        len(ready)
        * len(languages)
        * study["attempts_per_cell"]
        * study["pilot_mean_cost_usd"]
    )
    if projected > study["study_cost_limit_usd"]:
        errors.append(
            f"projected ${projected:.4f} exceeds study limit ${study['study_cost_limit_usd']:.4f}"
        )
    if require_launch_ready:
        if study.get("status") != "ready":
            errors.append("study status is not ready")
        if len(ready) < 3:
            errors.append("launch requires at least three ready task families")
    return errors


def build_schedule(study: dict) -> list[dict]:
    rng = random.Random(study["randomization_seed"])
    languages = study["languages"]
    ready = [family for family in study["task_families"] if family["status"] == "ready"]
    blocks = []
    for attempt in range(study["attempts_per_cell"]):
        family_order = ready[:]
        rng.shuffle(family_order)
        offset = rng.randrange(len(languages))
        language_order = languages[offset:] + languages[:offset]
        if rng.randrange(2):
            language_order = list(reversed(language_order))
        for family in family_order:
            for language in language_order:
                seed_text = f"{study['randomization_seed']}:{family['id']}:{attempt}:{language}"
                sample_seed = int(hashlib.sha256(seed_text.encode()).hexdigest()[:8], 16)
                blocks.append(
                    {
                        "task_family": family["id"],
                        "category": family["category"],
                        "project_maturity": family["project_maturity"],
                        "language": language,
                        "task_path": family["paths"][language],
                        "attempt": attempt + 1,
                        "sample_seed": sample_seed,
                    }
                )
    for order, row in enumerate(blocks, start=1):
        row["order_index"] = order
    return blocks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", default=str(ROOT / "study_v0.5.json"))
    parser.add_argument("--output")
    parser.add_argument("--require-launch-ready", action="store_true")
    args = parser.parse_args()
    study_path = pathlib.Path(args.study)
    study = load(study_path)
    errors = validate(study, args.require_launch_ready)
    schedule = build_schedule(study)
    projected = len(schedule) * study["pilot_mean_cost_usd"]
    receipt = {
        "schema_version": "1.0.0",
        "study_id": study["study_id"],
        "study_sha256": hashlib.sha256(study_path.read_bytes()).hexdigest(),
        "repo_revision": git_revision(),
        "launch_ready": not errors and study.get("status") == "ready",
        "validation_errors": errors,
        "planned_rollouts": len(schedule),
        "projected_cost_usd": round(projected, 8),
        "schedule": schedule,
    }
    text = json.dumps(receipt, indent=2) + "\n"
    if args.output:
        output = pathlib.Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(text.encode("utf-8"))
    else:
        print(text, end="")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
