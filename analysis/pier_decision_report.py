#!/usr/bin/env python3
"""Aggregate private Pier summaries into a GitHub Pages-safe language report."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import statistics
from collections import defaultdict

try:
    from analysis.pier_quality import extract as extract_quality
except ModuleNotFoundError:
    from pier_quality import extract as extract_quality

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = (
    ("decision-brownfield-rung1", "optimistic-concurrency", "brownfield", "simple", "primary"),
    ("decision-greenfield-rung1", "task-service-greenfield", "greenfield", "simple", "primary"),
    ("decision-schedule-rung1", "schedule-variants", None, "prefixed", "primary"),
    ("decision-python-example", "optimistic-concurrency", "brownfield", "simple", "example"),
    ("decision-go-example", "optimistic-concurrency", "brownfield", "simple", "example"),
)
TYPECHECK_CONFIG = {
    "javascript": "none",
    "typescript": "strict",
    "python": "none",
    "go": "default",
}


def wilson(passed: int, total: int, z: float = 1.959963984540054) -> list[float]:
    proportion = passed / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(
        proportion * (1 - proportion) / total + z * z / (4 * total * total)
    ) / denominator
    return [round(center - margin, 6), round(center + margin, 6)]


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_rows(jobs_dir: pathlib.Path) -> list[dict]:
    rows = []
    for job_name, family, fixed_maturity, mode, cohort in SOURCES:
        job_dir = jobs_dir / job_name
        if not job_dir.is_dir():
            raise SystemExit(f"missing required private Pier job: {job_dir}")
        for trial_dir in sorted(path for path in job_dir.iterdir() if path.is_dir()):
            result_path = trial_dir / "result.json"
            if not result_path.exists():
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result.get("exception_info") is not None:
                raise SystemExit(f"errored published trial: {trial_dir.name}")
            task_name = result["task_name"]
            if mode == "prefixed":
                maturity, language = task_name.split("-", 1)
            else:
                maturity, language = fixed_maturity, task_name
            agent = result["agent_result"]
            started = parse_time(result["agent_execution"]["started_at"])
            finished = parse_time(result["agent_execution"]["finished_at"])
            trajectory_path = trial_dir / "agent" / "trajectory.json"
            quality = (
                extract_quality(
                    json.loads(trajectory_path.read_text(encoding="utf-8")), result
                )
                if trajectory_path.is_file()
                else None
            )
            rows.append(
                {
                    "cohort": cohort,
                    "task_family": family,
                    "project_maturity": maturity,
                    "language": language,
                    "passed": result["verifier_result"]["rewards"]["reward"] == 1.0,
                    "input_tokens": agent["n_input_tokens"],
                    "cached_input_tokens": agent["n_cache_tokens"],
                    "output_tokens": agent["n_output_tokens"],
                    "cost_usd": agent["cost_usd"],
                    "agent_steps": agent["n_agent_steps"],
                    "agent_seconds": (finished - started).total_seconds(),
                    "finished_at": result["finished_at"],
                    "agent_version": result["agent_info"]["version"],
                    "model": result["config"]["agent"]["model_name"],
                    "quality": quality,
                }
            )
    return rows


def aggregate(rows: list[dict]) -> dict:
    total = len(rows)
    passed = sum(row["passed"] for row in rows)
    input_tokens = sum(row["input_tokens"] for row in rows)
    cached = sum(row["cached_input_tokens"] for row in rows)
    return {
        "runs": total,
        "passed": passed,
        "pass_rate": round(passed / total, 6),
        "pass_rate_wilson_95": wilson(passed, total),
        "total_cost_usd": round(sum(row["cost_usd"] for row in rows), 8),
        "mean_cost_usd": round(statistics.mean(row["cost_usd"] for row in rows), 8),
        "mean_input_tokens": round(statistics.mean(row["input_tokens"] for row in rows), 2),
        "mean_cached_input_tokens": round(
            statistics.mean(row["cached_input_tokens"] for row in rows), 2
        ),
        "cache_hit_rate": round(cached / input_tokens, 6),
        "mean_output_tokens": round(statistics.mean(row["output_tokens"] for row in rows), 2),
        "mean_agent_steps": round(statistics.mean(row["agent_steps"] for row in rows), 2),
        "mean_agent_seconds": round(statistics.mean(row["agent_seconds"] for row in rows), 2),
    }


def aggregate_quality(rows: list[dict]) -> dict:
    values = [row["quality"] for row in rows if row.get("quality")]
    first_known = [value["first_developer_verification_pass"] for value in values if value["first_developer_verification_pass"] is not None]
    return {
        "runs": len(values),
        "first_verification_observed": len(first_known),
        "first_verification_passed": sum(first_known),
        "first_verification_pass_rate": round(sum(first_known) / len(first_known), 6) if first_known else None,
        "verified_before_submit": sum(value["developer_verification_before_submit"] for value in values),
        "passing_verification_before_submit": sum(value["passing_developer_verification_before_submit"] for value in values),
        "mean_verification_attempts": round(statistics.mean(value["verification_attempts"] for value in values), 2) if values else None,
        "mean_static_check_invocations": round(statistics.mean(value["static_check_invocations"] for value in values), 2) if values else None,
        "malformed_actions": sum(value["malformed_actions"] for value in values),
        "patch_metrics_available": all(value["patch_statistics"]["files_changed"] is not None for value in values) if values else False,
    }

def format_optional_mean(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def relative_delta(other_value: float, base_value: float) -> float:
    return round((other_value / base_value - 1) * 100, 2)


def build_report(rows: list[dict]) -> dict:
    primary_rows = [row for row in rows if row["cohort"] == "primary"]
    example_rows = [row for row in rows if row["cohort"] == "example"]

    cells = []
    grouped = defaultdict(list)
    for row in primary_rows:
        grouped[(row["task_family"], row["project_maturity"], row["language"])].append(row)
    for key, items in sorted(grouped.items()):
        cells.append(
            {
                "task_family": key[0],
                "project_maturity": key[1],
                "language": key[2],
                "typecheck_config": TYPECHECK_CONFIG[key[2]],
                **aggregate(items),
            }
        )

    maturity_summaries = []
    contrasts = []
    for name in ("brownfield", "greenfield"):
        per_language = {}
        for language in ("javascript", "typescript"):
            items = [
                row
                for row in primary_rows
                if row["project_maturity"] == name and row["language"] == language
            ]
            summary = aggregate(items)
            maturity_summaries.append(
                {
                    "project_maturity": name,
                    "language": language,
                    "typecheck_config": TYPECHECK_CONFIG[language],
                    **summary,
                }
            )
            per_language[language] = summary
        javascript, typescript = per_language["javascript"], per_language["typescript"]
        contrasts.append(
            {
                "project_maturity": name,
                "typescript_minus_javascript_pass_rate": round(
                    typescript["pass_rate"] - javascript["pass_rate"], 6
                ),
                "typescript_relative_mean_cost_percent": relative_delta(
                    typescript["mean_cost_usd"], javascript["mean_cost_usd"]
                ),
                "typescript_relative_mean_input_percent": relative_delta(
                    typescript["mean_input_tokens"], javascript["mean_input_tokens"]
                ),
                "typescript_relative_mean_output_percent": relative_delta(
                    typescript["mean_output_tokens"], javascript["mean_output_tokens"]
                ),
                "typescript_relative_mean_steps_percent": relative_delta(
                    typescript["mean_agent_steps"], javascript["mean_agent_steps"]
                ),
                "typescript_relative_mean_agent_seconds_percent": relative_delta(
                    typescript["mean_agent_seconds"], javascript["mean_agent_seconds"]
                ),
            }
        )

    polyglot_examples = []
    example_groups = defaultdict(list)
    for row in example_rows:
        example_groups[(row["task_family"], row["project_maturity"], row["language"])].append(row)
    for key, items in sorted(example_groups.items()):
        polyglot_examples.append(
            {
                "task_family": key[0],
                "project_maturity": key[1],
                "language": key[2],
                "typecheck_config": TYPECHECK_CONFIG[key[2]],
                "interpretation": "illustrative_single_run",
                **aggregate(items),
            }
        )

    language_summaries = []
    for language in ("javascript", "typescript", "python", "go"):
        source_rows = (
            primary_rows
            if language in ("javascript", "typescript")
            else example_rows
        )
        items = [row for row in source_rows if row["language"] == language]
        language_summaries.append(
            {
                "language": language,
                "typecheck_config": TYPECHECK_CONFIG[language],
                "conditions": sorted({row["project_maturity"] for row in items}),
                "interpretation": (
                    "balanced_primary"
                    if language in ("javascript", "typescript")
                    else "illustrative_single_run"
                ),
                **aggregate(items),
            }
        )

    primary_summary = aggregate(primary_rows)
    published_summary = aggregate(rows)
    workflow_quality = [
        {
            "language": language,
            **aggregate_quality(
                [row for row in primary_rows if row["language"] == language]
            ),
        }
        for language in ("javascript", "typescript")
    ]

    return {
        "schema_version": "1.0.0",
        "benchmark_version": "0.4.0",
        "generated_at": max(row["finished_at"] for row in rows),
        "objective": "Test equivalent coding-agent work across JavaScript, TypeScript, Python, and Go without treating the languages as an undifferentiated leaderboard.",
        "model": rows[0]["model"],
        "model_settings": {
            "reasoning_effort": "low",
            "cache_control": "default_end",
            "per_rollout_cost_limit_usd": 0.1,
        },
        "agent": f"mini-swe-agent@{rows[0]['agent_version']}",
        "pier": "0.3.1",
        "scaffold": "mini-swe-agent/bash-only",
        "source_jobs": [source[0] for source in SOURCES],
        "all_published": published_summary,
        "primary": primary_summary,
        "cells": cells,
        "maturity_summaries": maturity_summaries,
        "contrasts": contrasts,
        "polyglot_examples": polyglot_examples,
        "language_summaries": language_summaries,
        "workflow_quality": workflow_quality,
        "finding": f"All {primary_summary['passed']} balanced JavaScript/TypeScript primary runs and both single Python/Go examples passed. Observed correctness tied; efficiency differences remain measurable, while Python and Go demonstrate end-to-end feasibility only.",
        "excluded": [
            "One earlier TypeScript cost-pilot pass was excluded because it was not part of a balanced JS/TS phase.",
            "One pre-model Windows proxy infrastructure failure was excluded and recorded no usage or cost.",
        ],
        "publication_boundary": "Aggregate Pier result summaries only; no prompts, trajectories, commands, patches, environment variables, or trial identifiers.",
    }


def render_markdown(report: dict) -> str:
    contrasts = {item["project_maturity"]: item for item in report["contrasts"]}
    summaries = {
        (item["project_maturity"], item["language"]): item
        for item in report["maturity_summaries"]
    }
    examples = {item["language"]: item for item in report["polyglot_examples"]}
    lines = [
        "# Language AI Bench: first cross-language report",
        "",
        "## Bottom line",
        "",
        f"**All {report['all_published']['runs']} published attempts passed. Correctness tied; workflow efficiency remains measurable.**",
        "",
        f"The balanced primary study contains {report['primary']['runs']} JavaScript/TypeScript attempts across new and existing Node projects. Python and Go each add one illustrative run of the existing optimistic-concurrency task. Those two 1/1 results prove that the calibrated four-language pipeline works end to end; they do not estimate Python or Go success rates and should not be compared as if they were equally sampled benchmark cells.",
        "",
        "## What the benchmark asked",
        "",
        "The first task requires an agent to add optimistic concurrency to a task service: stable ETags, required If-Match headers, stale-write rejection, correct deletion behavior, and protection against two conflicting writes both succeeding. The existing-project condition starts from working CRUD code. The new-project condition starts from a minimal Node scaffold.",
        "",
        "One fresh mini-swe-agent context receives one repository and the behavior-focused prompt. A shared language-neutral HTTP verifier grades the final service. A pass means the complete hidden behavior contract succeeded; 6/6 means six independent agent attempts passed, not six test cases.",
        "",
        "## Balanced JavaScript/TypeScript study",
        "",
        "| Condition | Language | Passed | Pass rate | Mean cost | Mean output | Mean steps | Mean agent time |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for maturity in ("brownfield", "greenfield"):
        for language in ("javascript", "typescript"):
            item = summaries[(maturity, language)]
            label = {"javascript": "JavaScript", "typescript": "TypeScript"}[language]
            lines.append(
                f"| {maturity.title()} | {label} | {item['passed']}/{item['runs']} | {item['pass_rate']:.0%} | ${item['mean_cost_usd']:.6f} | {item['mean_output_tokens']:.0f} | {item['mean_agent_steps']:.2f} | {item['mean_agent_seconds']:.2f}s |"
            )
    lines += ["", "Descriptive TypeScript-versus-JavaScript differences:", ""]
    for maturity in ("brownfield", "greenfield"):
        item = contrasts[maturity]
        lines.append(
            f"- **{maturity.title()}:** pass-rate difference 0 points; output tokens {item['typescript_relative_mean_output_percent']:+.2f}%, steps {item['typescript_relative_mean_steps_percent']:+.2f}%, cost {item['typescript_relative_mean_cost_percent']:+.2f}%, agent time {item['typescript_relative_mean_agent_seconds_percent']:+.2f}%."
        )
    lines += [
        "",
        "Every balanced cell reached 100%, so the observed accuracy difference is zero. This does not erase the comparison: TypeScript used fewer output tokens and steps but took longer wall-clock agent time. These continuous outcomes are descriptive estimates from a small set of related tasks, not yet a general language verdict.",
        "",
        "## Workflow quality among the 22 balanced runs",
        "",
        "| Language | First verifier pass | Mean verifier invocations | Passing verification before submit | Malformed actions |",
        "|---|---:|---:|---:|---:|",
        *[
            f"| {item['language'].replace('javascript', 'JavaScript').replace('typescript', 'TypeScript')} | {item['first_verification_passed']}/{item['first_verification_observed']} | {format_optional_mean(item['mean_verification_attempts'])} | {item['passing_verification_before_submit']}/{item['runs']} | {item['malformed_actions']} |"
            for item in report["workflow_quality"]
        ],
        "",
        "These trajectory-derived measures compare how the agent reached a correct result. They count explicit `scripts/verify-local` commands; checks performed inside that script are not separately visible. Patch-size and review metrics are unavailable because these Pier jobs did not retain final workspaces.",
        "",
        "## Python and Go examples",
        "",
        "| Language | Type feedback | Condition | Passed | Cost | Output | Steps | Agent time |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    feedback = {"python": "none", "go": "compiler"}
    for language in ("python", "go"):
        item = examples[language]
        lines.append(
            f"| {language.title()} | {feedback[language]} | Existing | {item['passed']}/{item['runs']} | ${item['mean_cost_usd']:.6f} | {item['mean_output_tokens']:.0f} | {item['mean_agent_steps']:.0f} | {item['mean_agent_seconds']:.2f}s |"
        )
    lines += [
        "",
        "Both examples passed the same hidden optimistic-concurrency verifier with no exceptions. Because each language has only one paid attempt, the result licenses only an end-to-end pipeline claim: this agent solved this instance once in Python and once in Go.",
        "",
        "## What the results support",
        "",
        "- The tested agent completed the optimistic-concurrency task at least once in all four language arms.",
        "- JavaScript and strict TypeScript completed every balanced new- and existing-project attempt.",
        "- Strict TypeScript imposed no observed completion penalty in the balanced study.",
        "",
        "## What the results do not support",
        "",
        "The report is not a four-language ranking. Python and Go have different ecosystems, compiler behavior, diagnostics, and likely model exposure, and each has only one agent attempt. The study also uses one model snapshot, low reasoning effort, a bash-only scaffold, related backend contracts, and no editor/LSP feedback. It does not measure long-term maintenance, frontend work, dependency migrations, human review, or future defect rates.",
        "",
        f"Total measured spend across all {report['all_published']['runs']} published attempts was **${report['all_published']['total_cost_usd']:.8f}**. Raw Pier jobs remain private; the public JSON contains aggregates only.",
        "",
        "See data/decision-results.json for machine-readable aggregates and confidence intervals.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", type=pathlib.Path, default=ROOT / "jobs")
    parser.add_argument(
        "--json-output",
        type=pathlib.Path,
        default=ROOT / "docs" / "data" / "decision-results.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=pathlib.Path,
        default=ROOT / "docs" / "DECISION_REPORT.md",
    )
    args = parser.parse_args()
    report = build_report(read_rows(args.jobs_dir))
    encoded = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    if b"sk-or-" in encoded or b"API_KEY" in encoded:
        raise SystemExit("secret-like content detected")
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_bytes(encoded)
    args.markdown_output.write_bytes(render_markdown(report).encode("utf-8"))
    print(
        f"wrote {args.json_output} and {args.markdown_output}: "
        f"{report['all_published']['passed']}/{report['all_published']['runs']} passes, "
        f"${report['all_published']['total_cost_usd']:.8f}"
    )


if __name__ == "__main__":
    main()
