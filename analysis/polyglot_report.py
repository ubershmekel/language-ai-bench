#!/usr/bin/env python3
"""Build the v0.5 report from prior and newly balanced private Pier jobs."""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from collections import defaultdict

try:
    from analysis.pier_decision_report import (
        SOURCES,
        aggregate,
        aggregate_quality,
        parse_time,
        read_rows,
    )
    from analysis.pier_quality import extract as extract_quality
except ModuleNotFoundError:
    from pier_decision_report import (
        SOURCES,
        aggregate,
        aggregate_quality,
        parse_time,
        read_rows,
    )
    from pier_quality import extract as extract_quality

ROOT = pathlib.Path(__file__).resolve().parents[1]
NEW_SOURCES = (
    ("v05-schedule-python", "schedule-variants", "brownfield", "python"),
    ("v05-schedule-go", "schedule-variants", "brownfield", "go"),
    ("v05-schedule-go-replacement", "schedule-variants", "brownfield", "go"),
    ("v05-occ-python-balance", "optimistic-concurrency", "brownfield", "python"),
    ("v05-occ-go-balance", "optimistic-concurrency", "brownfield", "go"),
)
LABELS = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "go": "Go",
}


def read_new_rows(jobs_dir: pathlib.Path) -> tuple[list[dict], list[dict]]:
    rows, excluded = [], []
    for job_name, family, maturity, language in NEW_SOURCES:
        job_dir = jobs_dir / job_name
        if not job_dir.is_dir():
            raise SystemExit(f"missing required v0.5 job: {job_dir}")
        for trial in sorted(path for path in job_dir.iterdir() if path.is_dir()):
            result_path = trial / "result.json"
            if not result_path.is_file():
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            agent = result.get("agent_result") or {}
            exception = result.get("exception_info")
            if exception:
                excluded.append(
                    {
                        "job": job_name,
                        "task_family": family,
                        "language": language,
                        "reason": exception["exception_type"],
                        "classification": "pre-submission-infrastructure",
                        "cost_usd": agent.get("cost_usd", 0),
                    }
                )
                continue
            trajectory = trial / "agent" / "trajectory.json"
            quality = extract_quality(
                json.loads(trajectory.read_text(encoding="utf-8")), result
            )
            started = parse_time(result["agent_execution"]["started_at"])
            finished = parse_time(result["agent_execution"]["finished_at"])
            rows.append(
                {
                    "cohort": "polyglot-balanced",
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
    return rows, excluded


def summary_rows(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    result = []
    for key, items in sorted(grouped.items()):
        result.append({**dict(zip(keys, key)), **aggregate(items)})
    return result


def build_report(jobs_dir: pathlib.Path) -> dict:
    prior = read_rows(jobs_dir)
    new_rows, excluded = read_new_rows(jobs_dir)
    all_valid = prior + new_rows
    polyglot = [
        row
        for row in prior
        if row["task_family"] == "optimistic-concurrency"
        or (
            row["task_family"] == "schedule-variants"
            and row["project_maturity"] == "brownfield"
        )
    ] + new_rows
    cells = summary_rows(polyglot, ("task_family", "language"))
    languages = summary_rows(polyglot, ("language",))
    workflow = []
    for language in LABELS:
        items = [row for row in polyglot if row["language"] == language]
        workflow.append({"language": language, **aggregate_quality(items)})
    total_spend = sum(row["cost_usd"] for row in all_valid) + sum(
        row["cost_usd"] for row in excluded
    )
    return {
        "schema_version": "1.0.0",
        "benchmark_version": "0.5.0-interim",
        "study_status": "balanced-retrospective-extension",
        "generated_at": max(row["finished_at"] for row in all_valid),
        "model": all_valid[0]["model"],
        "agent": f"mini-swe-agent@{all_valid[0]['agent_version']}",
        "all_published": aggregate(all_valid),
        "total_measured_spend_usd": round(total_spend, 8),
        "balanced_polyglot": aggregate(polyglot),
        "polyglot_cells": cells,
        "polyglot_languages": languages,
        "workflow_quality": workflow,
        "excluded_infrastructure": excluded,
        "source_jobs": [source[0] for source in SOURCES]
        + [source[0] for source in NEW_SOURCES],
        "finding": "All 20 valid attempts passed. Correctness is valid for the tested contracts; historical cross-language efficiency contrasts are exploratory because the pre-audit fixtures had inconsistent formatting and project topology.",
        "comparability_note": "The 2026-08-24 cohort predates the source-integrity gate. Several TypeScript, Go, and Python starters were unusually compressed, and schedule-variants used different source-file topology across languages.",
        "publication_boundary": "Aggregate result and trajectory-derived counts only; no prompts, commands, patches, trial IDs, or environment variables.",
    }


def render_markdown(report: dict) -> str:
    cells = {
        (row["task_family"], row["language"]): row for row in report["polyglot_cells"]
    }
    languages = {row["language"]: row for row in report["polyglot_languages"]}
    workflow = {row["language"]: row for row in report["workflow_quality"]}
    lines = [
        "# Language AI Bench: interim balanced polyglot report",
        "",
        "## Bottom line",
        "",
        f"**All {report['balanced_polyglot']['runs']} valid attempts in the balanced four-language brownfield cohort passed.** Correctness tied, while efficiency and workflow measurements still varied.",
        "",
        f"The full public history now contains {report['all_published']['runs']} valid completions, including the earlier JavaScript/TypeScript greenfield study. The new comparative cohort uses two matched existing-project task families with five runs per language: two optimistic-concurrency attempts and three schedule-data-model attempts.",
        "",
        "**Comparability warning:** this cohort predates the task-source integrity gate. Some TypeScript, Go, and Python starters were unusually compressed, and schedule-variants used different project topology across languages. The correctness results remain valid for the tested contracts; do not treat the recorded step, token, cost, or time differences as clean language effects.",
        "",
        "## Balanced results",
        "",
        "| Language | Optimistic concurrency | Schedule variants | Total | Mean cost | Mean output | Mean steps | Mean agent time |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for language in LABELS:
        first = cells[("optimistic-concurrency", language)]
        second = cells[("schedule-variants", language)]
        total = languages[language]
        lines.append(
            f"| {LABELS[language]} | {first['passed']}/{first['runs']} | {second['passed']}/{second['runs']} | {total['passed']}/{total['runs']} | ${total['mean_cost_usd']:.6f} | {total['mean_output_tokens']:.0f} | {total['mean_agent_steps']:.2f} | {total['mean_agent_seconds']:.2f}s |"
        )
    lines += [
        "",
        "## How the agent got there",
        "",
        "| Language | First verifier pass | Mean verifier invocations | Passing verification before submit | Malformed actions |",
        "|---|---:|---:|---:|---:|",
    ]
    for language in LABELS:
        item = workflow[language]
        lines.append(
            f"| {LABELS[language]} | {item['first_verification_passed']}/{item['first_verification_observed']} | {item['mean_verification_attempts']:.2f} | {item['passing_verification_before_submit']}/{item['runs']} | {item['malformed_actions']} |"
        )
    lines += [
        "",
        "These historical telemetry values describe the recorded runs, but fixture formatting and topology confound cross-language efficiency comparisons. Agent steps count model actions; agent time excludes container setup. Explicit verifier counts come from trajectories and do not split out checks performed inside scripts/verify-local.",
        "",
        "## Infrastructure exclusion and spend",
        "",
        f"One additional Go trial was excluded before submission because Pier's egress proxy temporarily failed DNS resolution. It consumed ${report['excluded_infrastructure'][0]['cost_usd']:.8f}; no completed patch was graded. Total measured provider spend, including that excluded event and the earlier study, was **${report['total_measured_spend_usd']:.8f}**.",
        "",
        "## Scope",
        "",
        "The 20-run comparison is balanced retrospectively across languages but was assembled in stages, before source-format and topology checks existed. It covers only two related backend task families, one model, one effort level, and one bash-only agent scaffold. The earlier 12 JavaScript/TypeScript greenfield runs remain published separately. A clean prospective rerun will supersede these efficiency estimates.",
        "",
        "See `data/polyglot-results.json` for machine-readable aggregates and `DECISION_REPORT.md` for the earlier report.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", type=pathlib.Path, default=ROOT / "jobs")
    parser.add_argument(
        "--json-output",
        type=pathlib.Path,
        default=ROOT / "docs" / "data" / "polyglot-results.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=pathlib.Path,
        default=ROOT / "docs" / "POLYGLOT_REPORT.md",
    )
    args = parser.parse_args()
    report = build_report(args.jobs_dir)
    encoded = (json.dumps(report, indent=2) + "\n").encode()
    if b"sk-or-" in encoded or b"API_KEY" in encoded:
        raise SystemExit("secret-like content detected")
    args.json_output.write_bytes(encoded)
    args.markdown_output.write_bytes(render_markdown(report).encode("utf-8"))
    print(
        f"wrote v0.5 report: {report['balanced_polyglot']['passed']}/{report['balanced_polyglot']['runs']} balanced passes; ${report['total_measured_spend_usd']:.8f} total spend"
    )


if __name__ == "__main__":
    main()
