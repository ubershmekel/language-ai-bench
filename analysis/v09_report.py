#!/usr/bin/env python3
"""Build the v0.9 report: three hard families, and whether any language leads.

v0.8 left one result standing above the rest. Its two hard families ranked the
five arms in nearly opposite orders, and each ordering followed from the
affordance the family rewards: `money-rollup` rewards exact rational arithmetic
in the standard library, `circuit-breaker` rewards not dropping a case of a
union that crosses module boundaries. Two families cannot say whether that is a
pattern or a coincidence.

v0.9 adds a third family that turns on a third thing. `text-redact` specifies
every offset and length in Unicode code points. Python indexes code points
already, JavaScript and TypeScript index UTF-16 code units, and Go indexes
bytes. `tsc` and `mypy` report nothing about the distinction, because `string`
is `string` whichever unit you meant, while `go build` forces `string` and
`[]rune` apart at every boundary. So this is the first family where the three
type-checked arms have no reason to behave alike.

The question this report answers is not "which language is best". It is whether
any language leads on all three families, and if not, whether the ordering
tracks the affordance each family rewards.

Agent wall time is deliberately absent. This cohort ran four rollouts at a time,
so elapsed time includes contention. Correctness, steps, tokens, and cost are
unaffected by concurrency.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import defaultdict

try:
    from analysis.v07_report import (
        attach_failed_cases,
        failure_profile,
        grouped,
        load,
        read_rows,
    )
    from analysis.v08_report import decisive, family_rankings, paired_contrasts
except ModuleNotFoundError:
    from v07_report import (
        attach_failed_cases,
        failure_profile,
        grouped,
        load,
        read_rows,
    )
    from v08_report import decisive, family_rankings, paired_contrasts

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARMS = ("javascript", "typescript", "python", "python-typed", "go")
LABELS = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "python-typed": "Python (typed)",
    "go": "Go",
}
REWARDS = {
    "money-rollup": "exact rational arithmetic in the standard library",
    "circuit-breaker": "not dropping a case of a union that crosses files",
    "text-redact": "knowing what a string is at runtime",
}
# Cases whose failure means the offsets were counted in the wrong unit.
CODE_POINT_CASES = ("code-point-offsets", "astral-mask")


def strip_timing(cells: list[dict]) -> list[dict]:
    """Drop elapsed-time summaries; concurrency makes them uncomparable."""
    return [
        {key: value for key, value in cell.items() if key != "mean_agent_seconds"}
        for cell in cells
    ]


def rate_table(report: dict) -> dict[str, dict[str, float]]:
    table: dict[str, dict[str, float]] = defaultdict(dict)
    for cell in report["by_family_and_arm"]:
        table[cell["task_family"]][cell["language"]] = cell["pass_rate"]
    return dict(table)


def leadership(report: dict) -> dict:
    """Does any arm lead, or trail, on every family that discriminates?"""
    table = rate_table(report)
    discriminating = {
        family: rates
        for family, rates in table.items()
        if max(rates.values()) > min(rates.values())
    }
    leaders, trailers = [], []
    for rates in discriminating.values():
        best, worst = max(rates.values()), min(rates.values())
        leaders.append({arm for arm, rate in rates.items() if rate == best})
        trailers.append({arm for arm, rate in rates.items() if rate == worst})
    everywhere_best = sorted(set.intersection(*leaders)) if leaders else []
    everywhere_worst = sorted(set.intersection(*trailers)) if trailers else []
    reversals = []
    families = sorted(discriminating)
    for index, left in enumerate(families):
        for right in families[index + 1 :]:
            for arm in ARMS:
                tops = discriminating[left][arm] == max(discriminating[left].values())
                bottoms = discriminating[right][arm] == min(
                    discriminating[right].values()
                )
                if tops and bottoms:
                    reversals.append(
                        {"language": arm, "best_on": left, "worst_on": right}
                    )
    return {
        "discriminating_families": families,
        "saturated_or_flat_families": sorted(set(table) - set(discriminating)),
        "best_on_every_discriminating_family": everywhere_best,
        "worst_on_every_discriminating_family": everywhere_worst,
        "reversals": reversals,
    }


def code_point_failures(rows: list[dict]) -> list[dict]:
    """How often each arm counted text-redact's offsets in the wrong unit."""
    counts: dict[str, dict[str, int]] = {
        arm: {"runs": 0, "code_point_case_failures": 0} for arm in ARMS
    }
    for row in rows:
        if row["task_family"] != "text-redact":
            continue
        entry = counts[row["language"]]
        entry["runs"] += 1
        if any(case in row.get("failed_cases", ()) for case in CODE_POINT_CASES):
            entry["code_point_case_failures"] += 1
    return [
        {
            "language": arm,
            **entry,
            "rate": (
                entry["code_point_case_failures"] / entry["runs"]
                if entry["runs"]
                else None
            ),
        }
        for arm, entry in counts.items()
    ]


def build_report(schedule: pathlib.Path, ledger: pathlib.Path) -> dict:
    excluded: list[dict] = []
    rows = read_rows(ledger, schedule, excluded)
    attach_failed_cases(rows, ledger)
    contrasts = paired_contrasts(rows, seed=20260828)
    receipt = load(schedule)
    report = {
        "schema_version": "1.0.0",
        "study_id": receipt["study_id"],
        "repo_revision": receipt["repo_revision"],
        "rollouts": len(rows),
        "excluded_infrastructure_failures": excluded,
        "total_cost_usd": round(sum(row["cost_usd"] for row in rows), 8),
        "by_arm": strip_timing(grouped(rows, ("language",))),
        "by_family_and_arm": strip_timing(grouped(rows, ("task_family", "language"))),
        "family_rankings": family_rankings(
            {"by_family_and_arm": grouped(rows, ("task_family", "language"))}
        ),
        "paired_contrasts": contrasts,
        "failure_profile": failure_profile(rows),
        "text_redact_code_point_failures": code_point_failures(rows),
        "decisive_correctness": decisive(contrasts, "hidden_test_pass"),
        "decisive_steps": decisive(contrasts, "agent_steps"),
        "notes": {
            "primary_estimand": (
                "per-family hidden-verifier pass rate by language, reported for "
                "all three families separately and never pooled into one score"
            ),
            "pooled_by_arm": (
                "the by_arm table pools three families that do not agree; it is "
                "reported for completeness and is not the estimand"
            ),
            "agent_seconds": (
                "not reported: this cohort ran four rollouts concurrently, so "
                "elapsed time includes contention"
            ),
            "stopping_rule": (
                "fixed at 120 rollouts, declared before the first paid call; no "
                "interim analysis informed continuation"
            ),
        },
    }
    report["leadership"] = leadership(report)
    return report


def render_markdown(report: dict) -> str:
    lead = report["leadership"]
    lines = [
        "# Language AI Bench v0.9: three hard families, and no winner",
        "",
        "## Why this study exists",
        "",
        "v0.8 ran two families hard enough to discriminate, and they ranked the",
        "five arms in nearly opposite orders. Each ordering followed from what the",
        "family rewards. Two families cannot tell you whether that is a pattern or",
        "a coincidence, so v0.9 adds a third that turns on a third thing.",
        "",
        "| Family | What it rewards |",
        "|---|---|",
    ]
    for family in sorted(REWARDS):
        lines.append(f"| `{family}` | {REWARDS[family]} |")
    lines += [
        "",
        "`text-redact` specifies every offset and length in Unicode code points.",
        "Python indexes code points already. JavaScript and TypeScript index",
        "UTF-16 code units, so an emoji counts as two. Go indexes bytes, so the",
        "same emoji counts as four. `tsc` and `mypy` report nothing about the",
        "difference, because `string` is `string` whichever unit you meant, while",
        "`go build` forces `string` and `[]rune` apart at every boundary. It is",
        "the first family where the three type-checked arms have no reason to",
        "behave alike.",
        "",
        f"**{report['rollouts']} rollouts, "
        f"${report['total_cost_usd']:.6f} measured spend.**",
        "",
        "## Results by family",
        "",
        "This is the estimand. The pooled table further down is not.",
        "",
        "| Family | Ordering |",
        "|---|---|",
    ]
    for item in report["family_rankings"]:
        order = " > ".join(
            f"{LABELS[arm]} {passed}/{runs}" for arm, passed, runs in item["order"]
        )
        lines.append(f"| `{item['task_family']}` | {order} |")
    lines += ["", "## Does any language lead everywhere?", ""]
    if lead["best_on_every_discriminating_family"]:
        winners = ", ".join(
            LABELS[arm] for arm in lead["best_on_every_discriminating_family"]
        )
        lines += [
            f"Yes: {winners} is top on every family that discriminates. That is a",
            "stronger result than v0.8 had, and it is the one case where a pooled",
            "number would not have been misleading.",
            "",
        ]
    else:
        lines += [
            "No. No language is top on every family that discriminates, and none",
            "is bottom on every one either. The v0.8 disagreement was not a",
            "coincidence of two tasks.",
            "",
        ]
    if lead["reversals"]:
        lines += ["Outright reversals, best on one family and worst on another:", ""]
        for item in lead["reversals"]:
            lines.append(
                f"- **{LABELS[item['language']]}**: best on `{item['best_on']}`, "
                f"worst on `{item['worst_on']}`"
            )
        lines.append("")
    if lead["saturated_or_flat_families"]:
        flat = ", ".join(f"`{name}`" for name in lead["saturated_or_flat_families"])
        lines += [
            f"{flat} came out flat across the arms and contributes no correctness",
            "signal in this cohort.",
            "",
        ]
    lines += [
        "## Counting the offsets in the wrong unit",
        "",
        "Two `text-redact` hidden cases fail specifically when the offsets are",
        "counted in UTF-16 code units or bytes rather than code points:",
        "`code-point-offsets` and `astral-mask`. Every other failure mode leaves",
        "them alone. This is the mechanism the family was built to expose.",
        "",
        "| Arm | Runs | Runs failing a code point case | Rate |",
        "|---|---:|---:|---:|",
    ]
    for entry in report["text_redact_code_point_failures"]:
        rate = "n/a" if entry["rate"] is None else f"{entry['rate']:.2f}"
        lines.append(
            f"| {LABELS[entry['language']]} | {entry['runs']} | "
            f"{entry['code_point_case_failures']} | {rate} |"
        )
    lines += [
        "",
        "## Results by family and arm",
        "",
        "| Family | Arm | Passed | Pass rate | Mean steps |",
        "|---|---|---:|---:|---:|",
    ]
    for cell in report["by_family_and_arm"]:
        lines.append(
            f"| {cell['task_family']} | {LABELS[cell['language']]} | "
            f"{cell['passed']}/{cell['runs']} | {cell['pass_rate']:.2f} | "
            f"{cell['mean_agent_steps']:.2f} |"
        )
    lines += [
        "",
        "## Pooled across all three families",
        "",
        "Reported for completeness. Pooling families that disagree produces a",
        "number that describes none of them, which is the whole point above.",
        "",
        "| Arm | Passed | Pass rate (95% CI) | Mean steps | Mean cost |",
        "|---|---:|---:|---:|---:|",
    ]
    for cell in report["by_arm"]:
        low, high = cell["pass_rate_ci95"]
        lines.append(
            f"| {LABELS[cell['language']]} | {cell['passed']}/{cell['runs']} | "
            f"{cell['pass_rate']:.2f} [{low:.2f}, {high:.2f}] | "
            f"{cell['mean_agent_steps']:.2f} | ${cell['mean_cost_usd']:.6f} |"
        )
    lines += ["", "## Contrasts whose interval excludes zero", ""]
    decisive_lines = report["decisive_correctness"] + report["decisive_steps"]
    if decisive_lines:
        lines += [f"- {line}" for line in decisive_lines]
    else:
        lines.append(
            "None. At this sample size no paired contrast separates from zero, "
            "which is a legitimate result and not a failed experiment."
        )
    lines += [
        "",
        "These are pooled over the three families and inherit the same warning:",
        "a pooled contrast between two arms is an average over tasks that",
        "disagree about the ordering.",
        "",
        "## Failing verifier cases",
        "",
        "| Arm | Failing cases |",
        "|---|---|",
    ]
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
        "rung, one bash-only scaffold. Three families is still below the point",
        "where between-family variance is well estimated, so this supports claims",
        "about these three tasks and no language-general claim.",
        "",
        "The stopping rule was fixed at 120 rollouts before the first paid call",
        "and no interim analysis informed continuation. v0.7's second batch was",
        "run because the first left an interval touching zero, which made that",
        "continuation outcome-dependent; this design does not repeat it.",
        "",
        "`text-redact` had never been run against a model before this cohort. Its",
        "difficulty was calibrated only in the free sense: the gate is green and",
        "the starter fails ten of the twelve checks. Where it landed is reported",
        "as a fact about the task, not adjusted afterwards.",
        "",
        "Agent wall time is not reported. This cohort ran four rollouts at a time,",
        "so elapsed time includes contention. All three families are command-mode,",
        "so no timing-sensitive verifier case was exposed to it.",
        "",
        "The families were chosen to reward different things, so their",
        "disagreement is partly by construction. That is the point: it shows the",
        "ordering is a property of the task, not of the language. It does not show",
        "how often real tickets look like any one of these three.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schedule", type=pathlib.Path, default=ROOT / "study_v0.9_luna_schedule.json"
    )
    parser.add_argument(
        "--ledger",
        type=pathlib.Path,
        default=ROOT / ".benchmark-state" / "v09-spend.json",
    )
    parser.add_argument(
        "--json-output",
        type=pathlib.Path,
        default=ROOT / "docs" / "data" / "v09-results.json",
    )
    parser.add_argument(
        "--markdown-output", type=pathlib.Path, default=ROOT / "docs" / "V09_REPORT.md"
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
