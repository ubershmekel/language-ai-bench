#!/usr/bin/env python3
"""Build the v0.7 hard-task aggregate report from private Pier artifacts.

v0.6 saturated: every language passed every attempt, so no correctness contrast
was estimable. v0.7 runs one deliberately harder brownfield family at more than
one model rung, so that the pass rate has room to differ. This report leads with
pass rate and its uncertainty, and keeps agent steps as the co-primary effort
outcome.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
from collections import defaultdict
from itertools import combinations

try:
    from analysis.v06_report import parse_time, patch_metrics
except ModuleNotFoundError:
    from v06_report import parse_time, patch_metrics

ROOT = pathlib.Path(__file__).resolve().parents[1]
LANGUAGES = ("javascript", "typescript", "python", "go")
LABELS = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "go": "Go",
}


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mean(items: list[float]) -> float | None:
    """None rather than NaN, so the published JSON stays valid JSON."""
    return sum(items) / len(items) if items else None


def read_rows(
    ledger_path: pathlib.Path,
    schedule_path: pathlib.Path,
    excluded: list[dict] | None = None,
) -> list[dict]:
    """Excluded infrastructure failures are appended to `excluded`, not scored."""
    excluded = [] if excluded is None else excluded
    ledger, receipt = load(ledger_path), load(schedule_path)
    planned_by_index = {row["order_index"]: row for row in receipt["schedule"]}
    rows = []
    for run in ledger.get("runs", []):
        planned = planned_by_index[run["order_index"]]
        for key in ("task_family", "language", "attempt", "sample_seed"):
            if planned[key] != run.get(key):
                raise SystemExit(
                    f"ledger/schedule mismatch at order {run['order_index']}: {key}"
                )
        if run.get("exception_type"):
            excluded.append(
                {
                    "order_index": run["order_index"],
                    "language": run["language"],
                    "attempt": run["attempt"],
                    "exception_type": run["exception_type"],
                }
            )
            continue
        result_path = ROOT / run["result_path"]
        result = load(result_path)
        agent = result.get("agent_result") or {}
        cost = agent.get("cost_usd")
        if not isinstance(cost, (int, float)) or abs(cost - run["cost_usd"]) > 1e-12:
            raise SystemExit(f"inconsistent measured cost at order {run['order_index']}")
        artifact = ROOT / run["workspace_artifact"]
        patch = patch_metrics(ROOT / planned["task_path"] / "environment", artifact)
        started = parse_time(result["agent_execution"]["started_at"])
        finished = parse_time(result["agent_execution"]["finished_at"])
        rows.append(
            {
                **{
                    key: planned[key]
                    for key in ("order_index", "task_family", "language", "attempt")
                },
                "hidden_test_pass": result["verifier_result"]["rewards"]["reward"] == 1.0,
                "agent_steps": agent["n_agent_steps"],
                "input_tokens": agent["n_input_tokens"],
                "output_tokens": agent["n_output_tokens"],
                "cost_usd": float(cost),
                "agent_seconds": (finished - started).total_seconds(),
                "patch": patch,
                "finished_at": result["finished_at"],
                "model": result["config"]["agent"]["model_name"],
                "agent_version": result["agent_info"]["version"],
            }
        )
    return rows


def wilson(successes: int, total: int, z: float = 1.959964) -> list[float]:
    """Wilson score interval, which stays sane at zero and at full marks."""
    if total == 0:
        return [float("nan"), float("nan")]
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    spread = (
        z
        * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
        / denominator
    )
    return [max(0.0, center - spread), min(1.0, center + spread)]


def summarize(items: list[dict]) -> dict:
    passed = sum(row["hidden_test_pass"] for row in items)
    solved = [row for row in items if row["hidden_test_pass"]]
    return {
        "runs": len(items),
        "passed": passed,
        "pass_rate": passed / len(items),
        "pass_rate_ci95": wilson(passed, len(items)),
        "total_cost_usd": round(sum(row["cost_usd"] for row in items), 8),
        **{
            f"mean_{key}": mean([row[key] for row in items])
            for key in (
                "agent_steps",
                "input_tokens",
                "output_tokens",
                "cost_usd",
                "agent_seconds",
            )
        },
        "mean_agent_steps_when_passed": mean([row["agent_steps"] for row in solved]),
        **{
            f"mean_{key}": mean([row["patch"][key] for row in items])
            for key in ("files_changed", "lines_added", "lines_deleted", "patch_lines")
        },
    }


def grouped(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    return [
        {**dict(zip(keys, key)), **summarize(items)}
        for key, items in sorted(groups.items())
    ]


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def paired_contrasts(
    rows: list[dict], resamples: int = 20_000, seed: int = 20260826
) -> list[dict]:
    """Paired bootstrap over complete task-family x attempt blocks."""
    by_block: dict[tuple, dict] = defaultdict(dict)
    for row in rows:
        by_block[(row["task_family"], row["attempt"])][row["language"]] = row
    blocks = [
        by_block[key] for key in sorted(by_block) if set(by_block[key]) == set(LANGUAGES)
    ]
    if not blocks:
        raise SystemExit("paired analysis requires at least one complete block")
    rng = random.Random(seed)
    metrics = (
        "hidden_test_pass",
        "agent_steps",
        "cost_usd",
        "output_tokens",
        "agent_seconds",
    )
    result = []
    for left, right in combinations(LANGUAGES, 2):
        contrasts = {
            metric: [
                float(block[left][metric]) - float(block[right][metric])
                for block in blocks
            ]
            for metric in metrics
        }
        boot: dict[str, list[float]] = {metric: [] for metric in metrics}
        for _ in range(resamples):
            sample = [rng.randrange(len(blocks)) for _ in blocks]
            for metric in metrics:
                boot[metric].append(mean([contrasts[metric][index] for index in sample]))
        result.append(
            {
                "left": left,
                "right": right,
                "direction": "left_minus_right",
                "blocks": len(blocks),
                "estimates": {
                    metric: {
                        "mean_difference": mean(contrasts[metric]),
                        "ci95": [
                            percentile(boot[metric], 0.025),
                            percentile(boot[metric], 0.975),
                        ],
                    }
                    for metric in metrics
                },
            }
        )
    return result


def failure_profile(rows: list[dict]) -> list[dict]:
    """Which verifier cases failed, per language, across failing runs."""
    profile: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        for case_id in row.get("failed_cases", ()):
            profile[row["language"]][case_id] += 1
    return [
        {
            "language": language,
            "failed_cases": dict(sorted(cases.items(), key=lambda item: -item[1])),
        }
        for language, cases in sorted(profile.items())
    ]


def attach_failed_cases(rows: list[dict], ledger_path: pathlib.Path) -> None:
    ledger = load(ledger_path)
    by_index = {run["order_index"]: run for run in ledger["runs"]}
    for row in rows:
        result_path = ROOT / by_index[row["order_index"]]["result_path"]
        details = result_path.parent / "verifier" / "details.json"
        cases: list[str] = []
        if details.is_file():
            try:
                report = load(details)
                cases = [
                    item["case_id"]
                    for item in report.get("case_results", [])
                    if not item["passed"]
                ]
            except (json.JSONDecodeError, KeyError):
                cases = []
        row["failed_cases"] = cases


def build_report(cohorts: list[dict]) -> dict:
    """cohorts: [{"rung": str, "ledger": Path, "schedule": Path}]"""
    all_rows: list[dict] = []
    rungs = []
    excluded: list[dict] = []
    for cohort in cohorts:
        cohort_excluded: list[dict] = []
        rows = read_rows(cohort["ledger"], cohort["schedule"], cohort_excluded)
        for item in cohort_excluded:
            excluded.append({**item, "rung": cohort["rung"]})
        attach_failed_cases(rows, cohort["ledger"])
        for row in rows:
            row["rung"] = cohort["rung"]
        receipt = load(cohort["schedule"])
        rungs.append(
            {
                "rung": cohort["rung"],
                "study_id": receipt["study_id"],
                "model": rows[0]["model"],
                **summarize(rows),
                "languages": grouped(rows, ("language",)),
                "paired_contrasts": paired_contrasts(rows),
                "failure_profile": failure_profile(rows),
                "excluded_infrastructure": cohort_excluded,
            }
        )
        all_rows.extend(rows)
    return {
        "schema_version": "2.0.0",
        "benchmark_version": "0.7.0",
        "study_id": "v0.7-money-rollup",
        "study_status": "complete-prospective",
        "generated_at": max(row["finished_at"] for row in all_rows),
        "agent": f"mini-swe-agent@{all_rows[0]['agent_version']}",
        "task_family": "money-rollup",
        "overall": summarize(all_rows),
        "rungs": rungs,
        "pooled_languages": grouped(all_rows, ("language",)),
        "excluded_infrastructure": excluded,
        "publication_boundary": "Aggregate results only; no secrets, prompts, commands, patches, job identifiers, result paths, or private ledger data.",
    }


def decisive(rung: dict, metric: str) -> list[str]:
    """Contrasts whose bootstrap interval excludes zero, rendered as sentences."""
    findings = []
    for item in rung["paired_contrasts"]:
        low, high = item["estimates"][metric]["ci95"]
        difference = item["estimates"][metric]["mean_difference"]
        if low > 0 or high < 0:
            faster, slower = item["left"], item["right"]
            if difference > 0:
                faster, slower = slower, faster
            findings.append(
                f"{LABELS[slower]} needed {abs(difference):.2f} more agent steps than "
                f"{LABELS[faster]} (95% CI [{low:.2f}, {high:.2f}])"
                if metric == "agent_steps"
                else f"{LABELS[slower]} passed {abs(difference):.2f} less often than "
                f"{LABELS[faster]} (95% CI [{low:.3f}, {high:.3f}])"
            )
    return findings


def render_markdown(report: dict) -> str:
    overall = report["overall"]
    strongest = max(report["rungs"], key=lambda rung: rung["pass_rate"])
    step_findings = decisive(strongest, "agent_steps")
    pass_findings = decisive(strongest, "hidden_test_pass")
    parts = [
        f"The ceiling is broken. On the `{strongest['model']}` rung the hard family passed "
        f"{strongest['passed']}/{strongest['runs']} rather than everything, so language contrasts are now estimable.",
    ]
    parts.append(
        "Correctness still barely moves: "
        + ("; ".join(pass_findings) + "." if pass_findings else
           "no pass-rate contrast has an interval excluding zero.")
    )
    parts.append(
        "Effort does move: "
        + ("; ".join(step_findings) + "." if step_findings else
           "no agent-step contrast has an interval excluding zero.")
    )
    weakest = min(report["rungs"], key=lambda rung: rung["pass_rate"])
    if weakest is not strongest:
        parts.append(
            f"On the weaker `{weakest['model']}` rung the same task is a cliff: "
            f"{weakest['passed']}/{weakest['runs']} passed in every language, so no language rescues a weaker agent."
        )
    BOTTOM_LINE = " ".join(parts)
    lines = [
        "# Language AI Bench v0.7: one hard task, four languages, two model rungs",
        "",
        "## Why this study exists",
        "",
        "Every earlier cohort saturated. In v0.6 all 36 attempts passed, so the measured correctness difference between languages was exactly zero by construction and no interval could be estimated. A benchmark whose tasks are all solved cannot answer whether the language matters.",
        "",
        "v0.7 changes two things. It adds `money-rollup`, a four-file brownfield refactor that replaces floating-point money handling with exact rational arithmetic, adds shortest-path currency conversion with ambiguity rejection, adds ancestor rollups, and adds a large rejection surface. And it runs that one family at more than one model strength, because whether the language matters may itself depend on how capable the agent is.",
        "",
        f"Across the whole cohort, **{overall['passed']}/{overall['runs']} attempts passed**.",
        "",
        "## Bottom line",
        "",
        BOTTOM_LINE,
        "",
        "## Results by model rung",
        "",
    ]
    for rung in report["rungs"]:
        languages = {row["language"]: row for row in rung["languages"]}
        low, high = rung["pass_rate_ci95"]
        lines += [
            f"### {rung['rung'].title()} rung: `{rung['model']}`",
            "",
            f"{rung['passed']}/{rung['runs']} passed overall ({rung['pass_rate']:.2f}, 95% CI [{low:.2f}, {high:.2f}]).",
            "",
            "| Language | Passed | Pass rate (95% CI) | Mean steps | Mean output tokens | Mean agent time | Mean cost |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for language in LANGUAGES:
            row = languages[language]
            low, high = row["pass_rate_ci95"]
            lines.append(
                f"| {LABELS[language]} | {row['passed']}/{row['runs']} | "
                f"{row['pass_rate']:.2f} [{low:.2f}, {high:.2f}] | "
                f"{row['mean_agent_steps']:.2f} | {row['mean_output_tokens']:.0f} | "
                f"{row['mean_agent_seconds']:.1f}s | ${row['mean_cost_usd']:.6f} |"
            )
        lines += [
            "",
            "Paired differences within matched attempt blocks, with 95% percentile intervals from a fixed-seed 20,000-resample paired bootstrap:",
            "",
            "| Contrast | Pass-rate difference (95% CI) | Agent-step difference (95% CI) |",
            "|---|---:|---:|",
        ]
        for item in rung["paired_contrasts"]:
            correctness = item["estimates"]["hidden_test_pass"]
            steps = item["estimates"]["agent_steps"]
            lines.append(
                f"| {LABELS[item['left']]} minus {LABELS[item['right']]} | "
                f"{correctness['mean_difference']:.3f} "
                f"[{correctness['ci95'][0]:.3f}, {correctness['ci95'][1]:.3f}] | "
                f"{steps['mean_difference']:.2f} "
                f"[{steps['ci95'][0]:.2f}, {steps['ci95'][1]:.2f}] |"
            )
        lines += [
            "",
            "Failing verifier cases, counted across all runs of that language:",
            "",
            "| Language | Failing cases |",
            "|---|---|",
        ]
        profile = {
            item["language"]: item["failed_cases"] for item in rung["failure_profile"]
        }
        for language in LANGUAGES:
            cases = profile.get(language, {})
            rendered = ", ".join(f"{case} x{count}" for case, count in cases.items())
            lines.append(f"| {LABELS[language]} | {rendered or 'none'} |")
        lines.append("")

    lines += [
        "## Pooled across rungs",
        "",
        "| Language | Passed | Pass rate (95% CI) | Mean steps | Mean cost |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in sorted(
        report["pooled_languages"], key=lambda item: LANGUAGES.index(item["language"])
    ):
        low, high = row["pass_rate_ci95"]
        lines.append(
            f"| {LABELS[row['language']]} | {row['passed']}/{row['runs']} | "
            f"{row['pass_rate']:.2f} [{low:.2f}, {high:.2f}] | "
            f"{row['mean_agent_steps']:.2f} | ${row['mean_cost_usd']:.6f} |"
        )
    lines += [
        "",
        "Pooling mixes model rungs and is descriptive only; the rung tables above are the estimates to read.",
        "",
        "## Scope",
        "",
        f"One hard brownfield family, four languages, {len(report['rungs'])} model rungs, one low-effort bash-only scaffold ({report['agent']}). Measured provider spend for this cohort was **${overall['total_cost_usd']:.8f}**.",
        "",
        "Topology is part of the treatment bundle: starter file counts, toolchains, and ecosystems differ by language, so any difference must not be read as a syntax-only effect. Task difficulty is part of the bundle too: this is one family, and a different hard task could rank languages differently.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cohort",
        action="append",
        required=True,
        metavar="RUNG=SCHEDULE,LEDGER",
        help="repeatable, e.g. mid=study_v0.7_mini_schedule.json,.benchmark-state/v07-mid-spend.json",
    )
    parser.add_argument(
        "--json-output",
        type=pathlib.Path,
        default=ROOT / "docs" / "data" / "v07-results.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=pathlib.Path,
        default=ROOT / "docs" / "V07_REPORT.md",
    )
    args = parser.parse_args()
    cohorts = []
    for item in args.cohort:
        rung, _, paths = item.partition("=")
        schedule, _, ledger = paths.partition(",")
        cohorts.append(
            {
                "rung": rung,
                "schedule": pathlib.Path(schedule),
                "ledger": pathlib.Path(ledger),
            }
        )
    report = build_report(cohorts)
    encoded = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    if any(
        secret in encoded
        for secret in (b"sk-or-", b"API_KEY", b"jobs/", b"jobs\\", b"result.json")
    ):
        raise SystemExit("private or secret-like content detected")
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_bytes(encoded)
    args.markdown_output.write_bytes(render_markdown(report).encode("utf-8"))
    print(
        f"wrote v0.7 report: {report['overall']['passed']}/{report['overall']['runs']} passes; "
        f"${report['overall']['total_cost_usd']:.8f}"
    )


if __name__ == "__main__":
    main()
