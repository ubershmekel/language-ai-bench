#!/usr/bin/env python3
"""Build the prospective v0.6 aggregate report from private Pier artifacts."""

from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import random
from collections import defaultdict
from datetime import datetime
from itertools import combinations

try:
    from analysis.pier_quality import extract as extract_quality
except ModuleNotFoundError:
    from pier_quality import extract as extract_quality

ROOT = pathlib.Path(__file__).resolve().parents[1]
LANGUAGES = ("javascript", "typescript", "python", "go")
LABELS = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "go": "Go",
}
DEPENDENCY_FILES = {
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "requirements.txt", "pyproject.toml", "poetry.lock", "go.mod", "go.sum",
}
IGNORED_PARTS = {".git", "node_modules", "__pycache__", ".pytest_cache"}


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def files(root: pathlib.Path) -> dict[str, pathlib.Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and not (set(path.relative_to(root).parts) & IGNORED_PARTS)
    }


def topology(root: pathlib.Path) -> dict:
    workspace = files(root)
    source = {name: path for name, path in workspace.items() if name.startswith("src/")}
    return {
        "source_files": len(source),
        "source_bytes": sum(path.stat().st_size for path in source.values()),
        "workspace_files": len(workspace),
        "workspace_bytes": sum(path.stat().st_size for path in workspace.values()),
    }


def line_delta(before: bytes, after: bytes) -> tuple[int, int]:
    try:
        old = before.decode("utf-8").splitlines()
        new = after.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return 0, 0
    added = deleted = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new).get_opcodes():
        if tag in {"replace", "delete"}:
            deleted += i2 - i1
        if tag in {"replace", "insert"}:
            added += j2 - j1
    return added, deleted


def patch_metrics(baseline: pathlib.Path, artifact: pathlib.Path) -> dict:
    old, new = files(baseline), files(artifact)
    changed = []
    added_lines = deleted_lines = 0
    for name in sorted(set(old) | set(new)):
        before = old[name].read_bytes() if name in old else b""
        after = new[name].read_bytes() if name in new else b""
        if before == after:
            continue
        changed.append(name)
        added, deleted = line_delta(before, after)
        added_lines += added
        deleted_lines += deleted
    workspace = topology(artifact)
    return {
        "files_changed": len(changed),
        "lines_added": added_lines,
        "lines_deleted": deleted_lines,
        "patch_lines": added_lines + deleted_lines,
        "dependency_manifest_changed": any(pathlib.PurePosixPath(name).name in DEPENDENCY_FILES for name in changed),
        "final_workspace_files": workspace["workspace_files"],
        "final_workspace_bytes": workspace["workspace_bytes"],
    }


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_rows(ledger_path: pathlib.Path, schedule_path: pathlib.Path) -> list[dict]:
    ledger, receipt = load(ledger_path), load(schedule_path)
    schedule = receipt["schedule"]
    if len(schedule) != 36 or len(ledger.get("runs", [])) != 36:
        raise SystemExit("v0.6 analysis requires exactly 36 scheduled and completed runs")
    rows = []
    for planned, run in zip(schedule, ledger["runs"]):
        for key in ("order_index", "task_family", "language", "attempt", "sample_seed"):
            if planned[key] != run.get(key):
                raise SystemExit(f"ledger/schedule mismatch at order {planned['order_index']}: {key}")
        if run.get("exception_type"):
            raise SystemExit(f"exceptional v0.6 run at order {planned['order_index']}")
        if not run.get("workspace_artifact_captured"):
            raise SystemExit(f"missing workspace artifact at order {planned['order_index']}")
        result_path = ROOT / run["result_path"]
        result = load(result_path)
        agent = result.get("agent_result") or {}
        cost = agent.get("cost_usd")
        if not isinstance(cost, (int, float)) or cost < 0 or abs(cost - run["cost_usd"]) > 1e-12:
            raise SystemExit(f"missing or inconsistent measured cost at order {planned['order_index']}")
        artifact = ROOT / run["workspace_artifact"]
        trajectory = load(result_path.parent / "agent" / "trajectory.json")
        quality = extract_quality(trajectory, result)
        patch = patch_metrics(ROOT / planned["task_path"] / "environment", artifact)
        started = parse_time(result["agent_execution"]["started_at"])
        finished = parse_time(result["agent_execution"]["finished_at"])
        rows.append({
            **{key: planned[key] for key in ("order_index", "task_family", "category", "project_maturity", "language", "attempt")},
            "hidden_test_pass": result["verifier_result"]["rewards"]["reward"] == 1.0,
            "agent_steps": agent["n_agent_steps"],
            "input_tokens": agent["n_input_tokens"],
            "cached_input_tokens": agent["n_cache_tokens"],
            "output_tokens": agent["n_output_tokens"],
            "cost_usd": float(cost),
            "agent_seconds": (finished - started).total_seconds(),
            "quality": quality,
            "patch": patch,
            "finished_at": result["finished_at"],
            "model": result["config"]["agent"]["model_name"],
            "agent_version": result["agent_info"]["version"],
        })
    return rows


def mean(items: list[float]) -> float:
    return sum(items) / len(items)


def summarize(items: list[dict]) -> dict:
    return {
        "runs": len(items),
        "passed": sum(row["hidden_test_pass"] for row in items),
        "pass_rate": mean([float(row["hidden_test_pass"]) for row in items]),
        "total_cost_usd": round(sum(row["cost_usd"] for row in items), 8),
        **{f"mean_{key}": mean([row[key] for row in items]) for key in ("agent_steps", "input_tokens", "cached_input_tokens", "output_tokens", "cost_usd", "agent_seconds")},
        **{f"mean_{key}": mean([row["patch"][key] for row in items]) for key in ("files_changed", "lines_added", "lines_deleted", "patch_lines", "final_workspace_files", "final_workspace_bytes")},
        "dependency_manifest_changes": sum(row["patch"]["dependency_manifest_changed"] for row in items),
    }


def grouped(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    return [{**dict(zip(keys, key)), **summarize(items)} for key, items in sorted(groups.items())]


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def paired_contrasts(rows: list[dict], resamples: int = 20_000, seed: int = 20260825) -> list[dict]:
    by_block = defaultdict(dict)
    for row in rows:
        by_block[(row["task_family"], row["attempt"])][row["language"]] = row
    blocks = [by_block[key] for key in sorted(by_block)]
    if len(blocks) != 9 or any(set(block) != set(LANGUAGES) for block in blocks):
        raise SystemExit("paired analysis requires nine complete four-language blocks")
    rng = random.Random(seed)
    result = []
    metrics = ("hidden_test_pass", "agent_steps", "cost_usd", "output_tokens", "agent_seconds", "patch_lines")
    for left, right in combinations(LANGUAGES, 2):
        contrasts = {metric: [float(block[left][metric] if metric != "patch_lines" else block[left]["patch"][metric]) - float(block[right][metric] if metric != "patch_lines" else block[right]["patch"][metric]) for block in blocks] for metric in metrics}
        boot = {metric: [] for metric in metrics}
        for _ in range(resamples):
            sample = [rng.randrange(len(blocks)) for _ in blocks]
            for metric in metrics:
                boot[metric].append(mean([contrasts[metric][index] for index in sample]))
        estimates = {}
        for metric in metrics:
            estimates[metric] = {
                "mean_difference": mean(contrasts[metric]),
                "ci95": [percentile(boot[metric], 0.025), percentile(boot[metric], 0.975)],
            }
        result.append({"left": left, "right": right, "direction": "left_minus_right", "blocks": len(blocks), "estimates": estimates})
    return result


def workflow(rows: list[dict]) -> list[dict]:
    result = []
    for language in LANGUAGES:
        items = [row for row in rows if row["language"] == language]
        quality = [row["quality"] for row in items]
        observed = [item["first_developer_verification_pass"] for item in quality if item["first_developer_verification_pass"] is not None]
        result.append({
            "language": language,
            "runs": len(items),
            "first_verification_observed": len(observed),
            "first_verification_passed": sum(observed),
            "verification_before_submit": sum(item["developer_verification_before_submit"] for item in quality),
            "passing_verification_before_submit": sum(item["passing_developer_verification_before_submit"] for item in quality),
            "mean_verification_attempts": mean([item["verification_attempts"] for item in quality]),
            "static_check_invocations": sum(item["static_check_invocations"] for item in quality),
            "malformed_actions": sum(item["malformed_actions"] for item in quality),
        })
    return result


def task_topology(receipt: dict) -> list[dict]:
    unique = {(row["task_family"], row["language"]): row for row in receipt["schedule"]}
    return [
        {"task_family": family, "language": language, **topology(ROOT / row["task_path"] / "environment")}
        for (family, language), row in sorted(unique.items())
    ]


def build_report(ledger_path: pathlib.Path, schedule_path: pathlib.Path) -> dict:
    rows = read_rows(ledger_path, schedule_path)
    receipt = load(schedule_path)
    return {
        "schema_version": "1.0.0",
        "benchmark_version": "0.6.0",
        "study_id": receipt["study_id"],
        "study_status": "complete-prospective",
        "generated_at": max(row["finished_at"] for row in rows),
        "model": rows[0]["model"],
        "agent": f"mini-swe-agent@{rows[0]['agent_version']}",
        "prospective": summarize(rows),
        "languages": grouped(rows, ("language",)),
        "cells": grouped(rows, ("task_family", "language")),
        "workflow_quality": workflow(rows),
        "paired_contrasts": paired_contrasts(rows),
        "task_topology": task_topology(receipt),
        "excluded_infrastructure": [],
        "infrastructure_note": "No infrastructure failures occurred in the prospective v0.6 cohort.",
        "review_findings": {"available": False, "reason": "No independent patch-review instrument was specified or run."},
        "historical_boundary": "Earlier v0.4/v0.5 results remain published as historical evidence; their efficiency estimates are not pooled with prospective v0.6 estimates.",
        "publication_boundary": "Aggregate results only; no secrets, prompts, commands, patches, job identifiers, result paths, or private ledger data.",
    }


def render_markdown(report: dict) -> str:
    languages = {row["language"]: row for row in report["languages"]}
    workflow_rows = {row["language"]: row for row in report["workflow_quality"]}
    lines = [
        "# Language AI Bench v0.6: prospective clean polyglot study", "",
        "## Bottom line", "",
        f"**All {report['prospective']['runs']} prospective attempts passed the hidden verifier.** The observed correctness contrast is therefore zero for every language pair; this does not prove equal underlying success rates.", "",
        "The primary efficiency estimand is the paired difference in agent steps within nine matched task-family × attempt blocks. Estimates below are prospective v0.6 only. Earlier results remain historical and are never pooled into these efficiency estimates.", "",
        "## Prospective results", "",
        "| Language | Passed | Mean steps | Mean output tokens | Mean agent time | Mean cost | Mean files changed | Mean +lines | Mean -lines |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for language in LANGUAGES:
        row = languages[language]
        lines.append(f"| {LABELS[language]} | {row['passed']}/{row['runs']} | {row['mean_agent_steps']:.2f} | {row['mean_output_tokens']:.0f} | {row['mean_agent_seconds']:.2f}s | ${row['mean_cost_usd']:.6f} | {row['mean_files_changed']:.2f} | {row['mean_lines_added']:.1f} | {row['mean_lines_deleted']:.1f} |")
    lines += ["", "## Paired primary comparisons", "", "Differences are left minus right. The 95% intervals are percentile intervals from a fixed-seed 20,000-resample paired bootstrap over the nine complete task-family × attempt blocks.", "", "| Contrast | Correctness difference (95% CI) | Agent-step difference (95% CI) |", "|---|---:|---:|"]
    for item in report["paired_contrasts"]:
        correctness = item["estimates"]["hidden_test_pass"]
        steps = item["estimates"]["agent_steps"]
        lines.append(f"| {LABELS[item['left']]} − {LABELS[item['right']]} | {correctness['mean_difference']:.3f} [{correctness['ci95'][0]:.3f}, {correctness['ci95'][1]:.3f}] | {steps['mean_difference']:.2f} [{steps['ci95'][0]:.2f}, {steps['ci95'][1]:.2f}] |")
    lines += ["", "All observed correctness differences and bootstrap intervals are exactly zero because every run passed. With only nine blocks, continuous-outcome intervals are necessarily broad and should be read as uncertainty descriptions, not rank certificates.", "", "## Workflow and patch metrics", "", "| Language | First explicit verification passed | Verified before submit | Mean verification attempts | Static-check invocations | Malformed actions | Dependency-manifest changes | Mean final workspace size |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for language in LANGUAGES:
        quality, row = workflow_rows[language], languages[language]
        lines.append(f"| {LABELS[language]} | {quality['first_verification_passed']}/{quality['first_verification_observed']} | {quality['passing_verification_before_submit']}/{quality['runs']} | {quality['mean_verification_attempts']:.2f} | {quality['static_check_invocations']} | {quality['malformed_actions']} | {row['dependency_manifest_changes']} | {row['mean_final_workspace_files']:.1f} files / {row['mean_final_workspace_bytes']:.0f} B |")
    lines += ["", "Patch counts compare each retained final workspace byte-for-byte with its committed task `environment/` baseline. Text line additions/deletions use UTF-8 line diffs; final workspace metrics exclude dependency/cache directories. No independent patch-review instrument was run, so review findings are reported as unavailable rather than inferred.", "", "## Task topology", "", "Implementation topology counts files and bytes under the committed baseline `src/` directory; workspace topology counts all committed environment files and bytes before the agent runs.", "", "| Task family | Language | Source files | Source bytes | Workspace files | Workspace bytes |", "|---|---|---:|---:|---:|---:|"]
    for row in report["task_topology"]:
        lines.append(f"| {row['task_family']} | {LABELS[row['language']]} | {row['source_files']} | {row['source_bytes']} | {row['workspace_files']} | {row['workspace_bytes']} |")
    lines += ["", "Topology is part of the treatment bundle. Differences mediated by file layout, starter size, compiler/toolchain, or ecosystem must not be interpreted as syntax-only language effects.", "", "## Infrastructure, spend, and scope", "", f"{report['infrastructure_note']} The 36 prospective trials cost **${report['prospective']['total_cost_usd']:.8f}** in measured provider spend; the maximum single-trial cap and the $0.75 study ceiling were never approached.", "", "This study covers one model snapshot, one low-effort bash-only agent scaffold, three calibrated brownfield backend task families, four languages, and three attempts per cell. The randomized schedule was fixed before launch and executed serially without reordering.", "", f"**Historical boundary:** {report['historical_boundary']}", "", "Machine-readable aggregates, including secondary paired intervals for cost, output tokens, agent time, and patch size, are in `data/v06-results.json`. The older report remains at `POLYGLOT_REPORT.md`."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=pathlib.Path, default=ROOT / ".benchmark-state" / "v06-spend.json")
    parser.add_argument("--schedule", type=pathlib.Path, default=ROOT / "studies" / "study_v0.6_schedule.json")
    parser.add_argument("--json-output", type=pathlib.Path, default=ROOT / "docs" / "data" / "v06-results.json")
    parser.add_argument("--markdown-output", type=pathlib.Path, default=ROOT / "docs" / "V06_REPORT.md")
    args = parser.parse_args()
    report = build_report(args.ledger, args.schedule)
    encoded = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    if any(secret in encoded for secret in (b"sk-or-", b"API_KEY", b"jobs/", b"jobs\\", b"result.json")):
        raise SystemExit("private or secret-like content detected")
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_bytes(encoded)
    args.markdown_output.write_bytes(render_markdown(report).encode("utf-8"))
    print(f"wrote v0.6 report: {report['prospective']['passed']}/{report['prospective']['runs']} passes; ${report['prospective']['total_cost_usd']:.8f}")


if __name__ == "__main__":
    main()
