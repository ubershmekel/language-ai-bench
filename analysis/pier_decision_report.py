#!/usr/bin/env python3
"""Aggregate private Pier summaries into a GitHub Pages-safe decision report."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import statistics
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = (
    ("decision-brownfield-rung1", "optimistic-concurrency", "brownfield", "simple"),
    ("decision-greenfield-rung1", "task-service-greenfield", "greenfield", "simple"),
    ("decision-schedule-rung1", "schedule-variants", None, "prefixed"),
)


def wilson(passed: int, total: int, z: float = 1.959963984540054) -> list[float]:
    proportion = passed / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return [round(center - margin, 6), round(center + margin, 6)]


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_rows(jobs_dir: pathlib.Path) -> list[dict]:
    rows = []
    for job_name, family, fixed_maturity, mode in SOURCES:
        job_dir = jobs_dir / job_name
        if not job_dir.is_dir():
            raise SystemExit(f"missing required private Pier job: {job_dir}")
        for trial_dir in sorted(path for path in job_dir.iterdir() if path.is_dir()):
            result_path = trial_dir / "result.json"
            if not result_path.exists():
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result.get("exception_info") is not None:
                raise SystemExit(f"errored primary trial: {trial_dir.name}")
            task_name = result["task_name"]
            if mode == "prefixed":
                maturity, language = task_name.split("-", 1)
            else:
                maturity, language = fixed_maturity, task_name
            agent = result["agent_result"]
            started = parse_time(result["agent_execution"]["started_at"])
            finished = parse_time(result["agent_execution"]["finished_at"])
            rows.append(
                {
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
        "mean_cached_input_tokens": round(statistics.mean(row["cached_input_tokens"] for row in rows), 2),
        "cache_hit_rate": round(cached / input_tokens, 6),
        "mean_output_tokens": round(statistics.mean(row["output_tokens"] for row in rows), 2),
        "mean_agent_steps": round(statistics.mean(row["agent_steps"] for row in rows), 2),
        "mean_agent_seconds": round(statistics.mean(row["agent_seconds"] for row in rows), 2),
    }


def relative_delta(ts_value: float, js_value: float) -> float:
    return round((ts_value / js_value - 1) * 100, 2)


def build_report(rows: list[dict]) -> dict:
    cells = []
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["task_family"], row["project_maturity"], row["language"])].append(row)
    for key, items in sorted(grouped.items()):
        cells.append({"task_family": key[0], "project_maturity": key[1], "language": key[2], **aggregate(items)})

    maturity = []
    contrasts = []
    for name in ("brownfield", "greenfield"):
        per_language = {}
        for language in ("javascript", "typescript"):
            items = [row for row in rows if row["project_maturity"] == name and row["language"] == language]
            summary = aggregate(items)
            maturity.append({"project_maturity": name, "language": language, **summary})
            per_language[language] = summary
        js, ts = per_language["javascript"], per_language["typescript"]
        contrasts.append(
            {
                "project_maturity": name,
                "typescript_minus_javascript_pass_rate": round(ts["pass_rate"] - js["pass_rate"], 6),
                "typescript_relative_mean_cost_percent": relative_delta(ts["mean_cost_usd"], js["mean_cost_usd"]),
                "typescript_relative_mean_input_percent": relative_delta(ts["mean_input_tokens"], js["mean_input_tokens"]),
                "typescript_relative_mean_output_percent": relative_delta(ts["mean_output_tokens"], js["mean_output_tokens"]),
                "typescript_relative_mean_steps_percent": relative_delta(ts["mean_agent_steps"], js["mean_agent_steps"]),
                "typescript_relative_mean_agent_seconds_percent": relative_delta(ts["mean_agent_seconds"], js["mean_agent_seconds"]),
            }
        )

    overall = aggregate(rows)
    return {
        "schema_version": "1.0.0",
        "benchmark_version": "0.3.0",
        "generated_at": max(row["finished_at"] for row in rows),
        "model": rows[0]["model"],
        "model_settings": {"reasoning_effort": "low", "cache_control": "default_end", "per_rollout_cost_limit_usd": 0.1},
        "agent": f"mini-swe-agent@{rows[0]['agent_version']}",
        "pier": "0.3.1",
        "scaffold": "mini-swe-agent/bash-only",
        "source_jobs": [source[0] for source in SOURCES],
        "primary": overall,
        "cells": cells,
        "maturity_summaries": maturity,
        "contrasts": contrasts,
        "excluded": [
            "One earlier TypeScript cost-pilot pass was excluded because it was not part of a balanced JS/TS phase.",
            "One pre-model Windows proxy infrastructure failure was excluded and recorded no usage or cost.",
        ],
        "finding": "All 22 balanced primary runs passed. Pass-rate superiority is not detectable because every cell hit the ceiling.",
        "publication_boundary": "Aggregate Pier result summaries only; no prompts, trajectories, commands, patches, environment variables, or trial identifiers.",
    }


def render_markdown(report: dict) -> str:
    contrasts = {item["project_maturity"]: item for item in report["contrasts"]}
    summaries = {(item["project_maturity"], item["language"]): item for item in report["maturity_summaries"]}
    lines = [
        "# JavaScript vs TypeScript for vibe-coded Node projects",
        "",
        "## Bottom line",
        "",
        "**Use TypeScript by default for projects you expect to keep or extend; use JavaScript for genuinely disposable scripts and tiny prototypes.**",
        "",
        "That recommendation is not based on a pass-rate win: all 22 balanced runs passed. Under GPT-5.6 Luna at low reasoning effort, both languages solved both greenfield and brownfield tasks, including the harder cross-file schedule-union change. TypeScript showed no completion penalty and used modestly fewer output tokens and agent steps, but its compile/test loop took longer wall-clock time. The practical recommendation therefore combines this no-penalty result with the unmeasured maintenance value of static checks; it is not proof that TypeScript makes agents more accurate.",
        "",
        "## Results by project maturity",
        "",
        "| Condition | Language | Passed | Pass rate | Mean cost | Mean output | Mean steps | Mean agent time |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for maturity in ("brownfield", "greenfield"):
        for language in ("javascript", "typescript"):
            item = summaries[(maturity, language)]
            language_label = {"javascript": "JavaScript", "typescript": "TypeScript"}[language]
            lines.append(
                f"| {maturity.title()} | {language_label} | {item['passed']}/{item['runs']} | {item['pass_rate']:.0%} | ${item['mean_cost_usd']:.6f} | {item['mean_output_tokens']:.0f} | {item['mean_agent_steps']:.2f} | {item['mean_agent_seconds']:.2f}s |"
            )
    lines += ["", "Descriptive TypeScript-versus-JavaScript differences:", ""]
    for maturity in ("brownfield", "greenfield"):
        item = contrasts[maturity]
        lines.append(
            f"- **{maturity.title()}:** pass-rate difference 0 points; output tokens {item['typescript_relative_mean_output_percent']:+.2f}%, steps {item['typescript_relative_mean_steps_percent']:+.2f}%, cost {item['typescript_relative_mean_cost_percent']:+.2f}%, agent time {item['typescript_relative_mean_agent_seconds_percent']:+.2f}%."
        )
    lines += [
        "",
        "## What the result licenses",
        "",
        "- For these two Node/HTTP contracts, this model/scaffold completed JavaScript and strict TypeScript equally often.",
        "- TypeScript did not make greenfield generation less likely to succeed and did not obstruct brownfield schema evolution.",
        "- The small efficiency differences are descriptive; with 5 brownfield and 6 greenfield runs per language, they are not stable population estimates.",
        "",
        "## What it does not license",
        "",
        "Every cell reached 100%, so the study cannot estimate a TypeScript accuracy advantage or establish equivalence. The 95% Wilson lower bound is only about 57% for 5/5 and 61% for 6/6. This is one model snapshot, low effort, a bash-only agent, two related backend contracts, and no LSP/editor feedback. It does not test React/Next.js ecosystems, long-lived maintenance, human review, dependency migrations, or defect rates after future changes.",
        "",
        "## Practical choice",
        "",
        "- **New application expected to grow:** TypeScript. The agent paid no observed success penalty, and future edits gain compiler feedback.",
        "- **Existing multi-file application:** TypeScript, more strongly. Cross-module schema changes are exactly where static contracts provide insurance, even though this model solved both arms.",
        "- **One-off automation, throwaway prototype, or tiny script:** JavaScript is reasonable when minimizing setup and compile latency matters more than future refactors.",
        "",
        f"Primary paid spend was **${report['primary']['total_cost_usd']:.8f}**. Raw Pier jobs remain private; the public JSON contains aggregates only.",
        "",
        "See [`data/decision-results.json`](data/decision-results.json) for machine-readable aggregates and confidence intervals.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", type=pathlib.Path, default=ROOT / "jobs")
    parser.add_argument("--json-output", type=pathlib.Path, default=ROOT / "docs" / "data" / "decision-results.json")
    parser.add_argument("--markdown-output", type=pathlib.Path, default=ROOT / "docs" / "DECISION_REPORT.md")
    args = parser.parse_args()
    report = build_report(read_rows(args.jobs_dir))
    encoded = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    if b"sk-or-" in encoded or b"API_KEY" in encoded:
        raise SystemExit("secret-like content detected")
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_bytes(encoded)
    args.markdown_output.write_bytes(render_markdown(report).encode("utf-8"))
    print(f"wrote {args.json_output} and {args.markdown_output}: {report['primary']['passed']}/{report['primary']['runs']} passes, ${report['primary']['total_cost_usd']:.8f}")


if __name__ == "__main__":
    main()
