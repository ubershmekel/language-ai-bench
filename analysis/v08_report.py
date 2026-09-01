#!/usr/bin/env python3
"""Build the v0.8 report: a within-language typing contrast across three families.

v0.7 estimated cross-language contrasts on one family and found Python ahead.
That comparison cannot separate typing from runtime, ecosystem, or pretraining
mass, and its hardest family turned out to discriminate on numeric semantics
rather than on anything a checker sees. v0.8 adds `python-typed` -- the same
interpreter and standard library, differing only in annotations and a blocking
`mypy --strict` step. JavaScript against TypeScript was already a same-language
typed/untyped pair, but TypeScript also brings a compile step and a build
toolchain; the Python pair holds those fixed, so it isolates the types alone.

Agent wall time is deliberately absent. This cohort ran four rollouts at a time,
so elapsed time includes contention and is not comparable to v0.7's serial
figures. Correctness, steps, tokens, and cost are unaffected by concurrency.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
from collections import defaultdict
from itertools import combinations

try:
    from analysis.v07_report import (
        attach_failed_cases,
        failure_profile,
        grouped,
        load,
        mean,
        percentile,
        read_rows,
        summarize,
    )
except ModuleNotFoundError:
    from v07_report import (
        attach_failed_cases,
        failure_profile,
        grouped,
        load,
        mean,
        percentile,
        read_rows,
        summarize,
    )

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARMS = ("javascript", "typescript", "python", "python-typed", "go")
LABELS = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "python-typed": "Python (typed)",
    "go": "Go",
}
PRIMARY = ("python-typed", "python")
# agent_seconds is excluded on purpose: see the module docstring.
METRICS = ("hidden_test_pass", "agent_steps", "cost_usd", "output_tokens")


def paired_contrasts(
    rows: list[dict], resamples: int = 20_000, seed: int = 20260827
) -> list[dict]:
    """Paired bootstrap over complete task-family x attempt blocks."""
    by_block: dict[tuple, dict] = defaultdict(dict)
    for row in rows:
        by_block[(row["task_family"], row["attempt"])][row["language"]] = row
    blocks = [
        by_block[key] for key in sorted(by_block) if set(by_block[key]) == set(ARMS)
    ]
    if not blocks:
        raise SystemExit("paired analysis requires at least one complete block")
    rng = random.Random(seed)
    result = []
    for left, right in combinations(ARMS, 2):
        contrasts = {
            metric: [
                float(block[left][metric]) - float(block[right][metric])
                for block in blocks
            ]
            for metric in METRICS
        }
        boot: dict[str, list[float]] = {metric: [] for metric in METRICS}
        for _ in range(resamples):
            sample = [rng.randrange(len(blocks)) for _ in blocks]
            for metric in METRICS:
                boot[metric].append(
                    mean([contrasts[metric][index] for index in sample])
                )
        result.append(
            {
                "left": left,
                "right": right,
                "direction": "left_minus_right",
                "blocks": len(blocks),
                "primary": (left, right) == PRIMARY or (right, left) == PRIMARY,
                "estimates": {
                    metric: {
                        "mean_difference": mean(contrasts[metric]),
                        "ci95": [
                            percentile(boot[metric], 0.025),
                            percentile(boot[metric], 0.975),
                        ],
                    }
                    for metric in METRICS
                },
            }
        )
    return result


def decisive(contrasts: list[dict], metric: str) -> list[str]:
    """Contrasts whose bootstrap interval excludes zero, rendered as sentences."""
    lines = []
    for item in contrasts:
        low, high = item["estimates"][metric]["ci95"]
        if low <= 0 <= high:
            continue
        difference = item["estimates"][metric]["mean_difference"]
        left, right = LABELS[item["left"]], LABELS[item["right"]]
        unit = "passed" if metric == "hidden_test_pass" else "used"
        lines.append(
            f"{left} {unit} {abs(difference):.3f} "
            f"{'more' if difference > 0 else 'less'} often than {right} "
            f"(95% CI [{low:.3f}, {high:.3f}])"
            if metric == "hidden_test_pass"
            else f"{left} needed {abs(difference):.2f} "
            f"{'more' if difference > 0 else 'fewer'} {metric.replace('_', ' ')} "
            f"than {right} (95% CI [{low:.3f}, {high:.3f}])"
        )
    return lines


def oriented_primary(contrasts: list[dict]) -> dict:
    """The primary contrast, always oriented as python-typed minus python.

    `combinations` yields ("python", "python-typed"), so the stored difference
    runs untyped minus typed. Reporting it without flipping would invert the
    headline, so the orientation is pinned here rather than at render time.
    """
    item = next(entry for entry in contrasts if entry["primary"])
    flip = item["left"] == PRIMARY[1]
    return {
        "left": PRIMARY[0],
        "right": PRIMARY[1],
        "direction": "left_minus_right",
        "blocks": item["blocks"],
        "estimates": {
            metric: {
                "mean_difference": -value["mean_difference"]
                if flip
                else value["mean_difference"],
                "ci95": sorted(
                    [-value["ci95"][0], -value["ci95"][1]]
                    if flip
                    else value["ci95"]
                ),
            }
            for metric, value in item["estimates"].items()
        },
    }


def family_rankings(report: dict) -> list[dict]:
    """Arms ordered by pass rate within each family, best first."""
    by_family: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for cell in report["by_family_and_arm"]:
        by_family[cell["task_family"]].append(
            (cell["language"], cell["passed"], cell["runs"])
        )
    result = []
    for family, cells in sorted(by_family.items()):
        order = sorted(cells, key=lambda item: (-item[1] / item[2], item[0]))
        rates = [passed / runs for _, passed, runs in cells]
        result.append(
            {
                "task_family": family,
                "order": order,
                "spread": round(max(rates) - min(rates), 6),
            }
        )
    return result


def strip_timing(cells: list[dict]) -> list[dict]:
    """Drop elapsed-time summaries; concurrency makes them uncomparable."""
    return [
        {key: value for key, value in cell.items() if key != "mean_agent_seconds"}
        for cell in cells
    ]


def build_report(schedule: pathlib.Path, ledger: pathlib.Path) -> dict:
    excluded: list[dict] = []
    rows = read_rows(ledger, schedule, excluded)
    attach_failed_cases(rows, ledger)
    contrasts = paired_contrasts(rows)
    return {
        "schema_version": "1.0.0",
        "primary_contrast": oriented_primary(contrasts),
        "study_id": load(schedule)["study_id"],
        "repo_revision": load(schedule)["repo_revision"],
        "rollouts": len(rows),
        "excluded_infrastructure_failures": excluded,
        "total_cost_usd": round(sum(row["cost_usd"] for row in rows), 8),
        "by_arm": strip_timing(grouped(rows, ("language",))),
        "by_family_and_arm": strip_timing(
            grouped(rows, ("task_family", "language"))
        ),
        "paired_contrasts": contrasts,
        "failure_profile": failure_profile(rows),
        "decisive_correctness": decisive(contrasts, "hidden_test_pass"),
        "decisive_steps": decisive(contrasts, "agent_steps"),
        "notes": {
            "primary_estimand": (
                "paired python-typed minus python hidden-verifier pass rate, "
                "pooled over three families"
            ),
            "agent_seconds": (
                "not reported: this cohort ran four rollouts concurrently, so "
                "elapsed time includes contention and is not comparable to the "
                "serial v0.7 figures"
            ),
            "stopping_rule": (
                "fixed at 120 rollouts, declared before the first paid call; no "
                "interim analysis informed continuation"
            ),
        },
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Language AI Bench v0.8: does typing help, holding the language fixed?",
        "",
        "## Why this study exists",
        "",
        "v0.7 found Python ahead of JavaScript and Go on one hard family. That",
        "contrast cannot separate typing from runtime, ecosystem, diagnostics, or",
        "pretraining mass, and its failure table showed the family discriminating",
        "on rounding mode, negative-zero formatting, and rejection coverage --",
        "none of which a type checker sees. The untyped language sweeping such a",
        "task is not evidence about typing.",
        "",
        "v0.8 adds `python-typed`: the same interpreter, standard library, and",
        "file topology as `python`, differing only in annotations and a blocking",
        "`mypy --strict` step in the developer loop. That gives two same-language",
        "pairs rather than one. JavaScript against TypeScript already varied types,",
        "but TypeScript also adds a compile step and a build toolchain; the Python",
        "pair holds both of those fixed, so reading the two together separates",
        "types from build. It also adds `circuit-breaker`, a family whose difficulty",
        "is routed through a state machine and an outcome union crossing module",
        "boundaries, where a missed case is silent in JavaScript and Python and",
        "visible to `tsc`, `go build`, and `mypy`.",
        "",
        f"**{report['rollouts']} rollouts, ${report['total_cost_usd']:.6f} measured spend.**",
        "",
        "## Results by arm",
        "",
        "| Arm | Passed | Pass rate (95% CI) | Mean steps | Mean output tokens | Mean cost |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cell in report["by_arm"]:
        low, high = cell["pass_rate_ci95"]
        lines.append(
            f"| {LABELS[cell['language']]} | {cell['passed']}/{cell['runs']} | "
            f"{cell['pass_rate']:.2f} [{low:.2f}, {high:.2f}] | "
            f"{cell['mean_agent_steps']:.2f} | {cell['mean_output_tokens']:.0f} | "
            f"${cell['mean_cost_usd']:.6f} |"
        )
    lines += ["", "## The primary contrast", ""]
    primary = report["primary_contrast"]
    if primary:
        estimate = primary["estimates"]["hidden_test_pass"]
        low, high = estimate["ci95"]
        verdict = (
            "excludes zero" if not (low <= 0 <= high) else "includes zero"
        )
        lines += [
            f"Typed Python minus untyped Python on pass rate: "
            f"**{estimate['mean_difference']:+.3f}**, 95% CI "
            f"[{low:.3f}, {high:.3f}] over {primary['blocks']} matched blocks. "
            f"The interval {verdict}.",
            "",
        ]
        steps = primary["estimates"]["agent_steps"]
        slow, shigh = steps["ci95"]
        lines += [
            f"On agent steps the same pair differs by "
            f"**{steps['mean_difference']:+.2f}**, 95% CI [{slow:.2f}, {shigh:.2f}] "
            "-- the cost side of the same treatment.",
            "",
        ]
    lines += ["## Results by family and arm", "", "| Family | Arm | Passed | Pass rate | Mean steps |", "|---|---|---:|---:|---:|"]
    for cell in report["by_family_and_arm"]:
        lines.append(
            f"| {cell['task_family']} | {LABELS[cell['language']]} | "
            f"{cell['passed']}/{cell['runs']} | {cell['pass_rate']:.2f} | "
            f"{cell['mean_agent_steps']:.2f} |"
        )
    lines += ["", "## Where the families disagree", ""]
    ranked = family_rankings(report)
    discriminating = [item for item in ranked if item["spread"] > 0]
    if len(discriminating) >= 2:
        lines += [
            "The design says to report per-family results in full even when they",
            "contradict the aggregate, because disagreement across families is",
            "itself a finding. Here it is the main one.",
            "",
        ]
        for item in discriminating:
            order = " > ".join(
                f"{LABELS[arm]} {passed}/{runs}"
                for arm, passed, runs in item["order"]
            )
            lines.append(f"- **{item['task_family']}**: {order}")
        lines += [
            "",
            "The two families that discriminate rank the arms in close to opposite",
            "orders. Pooling them produces an aggregate that describes neither.",
            "That is the concrete form of the warning this repository has carried",
            "since v0.1: a single benchmark score across task families would have",
            "hidden this completely.",
            "",
        ]
    saturated = [item["task_family"] for item in ranked if item["spread"] == 0]
    if saturated:
        lines += [
            f"{', '.join(saturated)} saturated at 100% in every arm, as expected "
            "from v0.6, and contributes no correctness signal.",
            "",
        ]
    lines += ["## Contrasts whose interval excludes zero", ""]
    decisive_lines = report["decisive_correctness"] + report["decisive_steps"]
    if decisive_lines:
        lines += [f"- {line}" for line in decisive_lines]
    else:
        lines.append(
            "None. At this sample size no paired contrast separates from zero, "
            "which is a legitimate result and not a failed experiment."
        )
    lines += ["", "## Failing verifier cases", "", "| Arm | Failing cases |", "|---|---|"]
    for entry in report["failure_profile"]:
        cases = ", ".join(
            f"{case} x{count}" for case, count in entry["failed_cases"].items()
        )
        lines.append(f"| {LABELS[entry['language']]} | {cases or 'none'} |")
    lines += [
        "",
        "## Scope and limits",
        "",
        "Three brownfield families, five arms, eight attempts per cell, one model",
        "rung, one bash-only scaffold. Three families is below the point where",
        "between-family variance dominates, so this estimates the arms at these",
        "three tasks and supports no language-general claim.",
        "",
        "The stopping rule was fixed at 120 rollouts before the first paid call",
        "and no interim analysis informed continuation. v0.7's second batch was",
        "run because the first left an interval touching zero, which made that",
        "continuation outcome-dependent; this design does not repeat it.",
        "",
        "Agent wall time is not reported. This cohort ran four rollouts at a time,",
        "so elapsed time includes contention and is not comparable to v0.7's",
        "serial figures. Correctness, steps, tokens, and cost are unaffected by",
        "concurrency, and all three families here are command-mode, so no",
        "timing-sensitive verifier case was exposed to it.",
        "",
        "`python-typed` carries one asymmetry worth naming: `verify-local` runs",
        "`mypy` before the developer tests, so a type error blocks that loop. Real",
        "Python projects vary in whether their checker is advisory or blocking.",
        "This arm is the blocking case, which is the stronger dose.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schedule", type=pathlib.Path, default=ROOT / "studies" / "study_v0.8_luna_schedule.json"
    )
    parser.add_argument(
        "--ledger",
        type=pathlib.Path,
        default=ROOT / ".benchmark-state" / "v08-spend.json",
    )
    parser.add_argument(
        "--json-output", type=pathlib.Path, default=ROOT / "docs" / "data" / "v08-results.json"
    )
    parser.add_argument(
        "--markdown-output", type=pathlib.Path, default=ROOT / "docs" / "V08_REPORT.md"
    )
    args = parser.parse_args()
    report = build_report(args.schedule, args.ledger)
    encoded = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    for secret in (b"sk-or-", b"API_KEY", b"jobs/", b"jobs\\", b"result.json"):
        if secret in encoded:
            raise SystemExit(f"refusing to publish: report contains {secret!r}")
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_bytes(encoded)
    args.markdown_output.write_text(
        render_markdown(report), encoding="utf-8", newline="\n"
    )
    print(f"wrote {args.json_output} and {args.markdown_output}")


if __name__ == "__main__":
    main()
