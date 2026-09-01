#!/usr/bin/env python3
"""Build the v0.9 report: a third hard family that turned out not to be hard.

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

It did not work. `text-redact` passed 39 of 40 and its code point hazard never
fired once, so it cannot rank anything. The report says so first, then falls
back to what the cohort can answer: whether the two carried-over families still
disagree, and how far their orderings moved on nothing but a new seed.

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
    from analysis.v08_report import (
        decisive,
        family_rankings,
        oriented_primary,
        paired_contrasts,
    )
except ModuleNotFoundError:
    from v07_report import (
        attach_failed_cases,
        failure_profile,
        grouped,
        load,
        read_rows,
    )
    from v08_report import (
        decisive,
        family_rankings,
        oriented_primary,
        paired_contrasts,
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


def leadership(report: dict, minimum_spread: int = 2) -> dict:
    """Does any arm lead, or trail, on every family that discriminates?

    A family counts as discriminating only if its best and worst arms differ by
    at least `minimum_spread` runs. One run of separation out of eight is not an
    ordering, and treating it as one manufactures reversals out of noise.
    """
    table = rate_table(report)
    spread_runs = {
        cell["task_family"]: 0 for cell in report["by_family_and_arm"]
    }
    for family in spread_runs:
        counts = [
            cell["passed"]
            for cell in report["by_family_and_arm"]
            if cell["task_family"] == family
        ]
        spread_runs[family] = max(counts) - min(counts)
    discriminating = {
        family: rates
        for family, rates in table.items()
        if spread_runs[family] >= minimum_spread
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
        "minimum_spread_runs": minimum_spread,
        "spread_runs": spread_runs,
        "discriminating_families": families,
        "flat_families": sorted(set(table) - set(discriminating)),
        "best_on_every_discriminating_family": everywhere_best,
        "worst_on_every_discriminating_family": everywhere_worst,
        "reversals": reversals,
    }


def cohort_drift(report: dict, previous: pathlib.Path) -> list[dict]:
    """Same family, same design, previous cohort: how much did the order move?"""
    if not previous.is_file():
        return []
    before: dict[tuple[str, str], tuple[int, int]] = {
        (cell["task_family"], cell["language"]): (cell["passed"], cell["runs"])
        for cell in load(previous)["by_family_and_arm"]
    }
    drift = []
    for cell in report["by_family_and_arm"]:
        key = (cell["task_family"], cell["language"])
        if key not in before:
            continue
        passed, runs = before[key]
        drift.append(
            {
                "task_family": cell["task_family"],
                "language": cell["language"],
                "v08_passed": passed,
                "v08_runs": runs,
                "v09_passed": cell["passed"],
                "v09_runs": cell["runs"],
                "change_runs": cell["passed"] - passed,
            }
        )
    return drift


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
        # The site reads this field. It is the same within-language pair v0.8
        # made primary, kept for continuity; v0.9's own estimand is per-family.
        "primary_contrast": oriented_primary(contrasts),
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
    report["cohort_drift"] = cohort_drift(
        report, ROOT / "docs" / "data" / "v08-results.json"
    )
    return report


def render_markdown(report: dict) -> str:
    lead = report["leadership"]
    redact_cells = [
        item
        for item in report["by_family_and_arm"]
        if item["task_family"] == "text-redact"
    ]
    redact_passed = sum(item["passed"] for item in redact_cells)
    redact_runs = sum(item["runs"] for item in redact_cells)
    code_point_total = sum(
        item["code_point_case_failures"]
        for item in report["text_redact_code_point_failures"]
    )
    lines = [
        "# Language AI Bench v0.9: the new family was too easy, and the old ones moved",
        "",
        "## What this cohort was for",
        "",
        "v0.8 ran two families hard enough to discriminate and they ranked the",
        "five arms in nearly opposite orders. Each ordering followed from what the",
        "family rewards. Two families cannot say whether that is a pattern or a",
        "coincidence, so v0.9 added a third that turns on a third thing.",
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
        "`go build` forces `string` and `[]rune` apart at every boundary.",
        "",
        f"**{report['rollouts']} rollouts, "
        f"${report['total_cost_usd']:.6f} measured spend.**",
        "",
        "## Headline: it did not work",
        "",
        f"`text-redact` passed {redact_passed} of {redact_runs} across the five "
        "arms, so it cannot rank them. Worse for the hypothesis it was built to "
        "test, the code point hazard never fired: of those "
        f"{redact_runs} runs, {code_point_total} failed either of the two hidden "
        "cases that catch offsets counted in UTF-16 code units or bytes.",
        "",
        "The likely cause is a task-design mistake and it is worth naming",
        "precisely. The instruction states the code point rule in its own",
        "paragraph and adds that it does not matter how your language happens to",
        "index a string. That is a loud warning sitting directly on the hazard,",
        "so every arm converted to a code point array up front and the trap was",
        "never sprung. The rule has to be stated somewhere, but it did not need a",
        "paragraph of its own, and the two developer tests could have been ASCII",
        "only with the astral cases left entirely hidden. That is the fix for a",
        "v1.0 revision, and it is a change to the task, not to this result.",
        "",
        "## Results by family",
        "",
        "This is the estimand. The pooled table further down is not.",
        "",
        "| Family | Spread | Ordering |",
        "|---|---:|---|",
    ]
    for item in report["family_rankings"]:
        order = " > ".join(
            f"{LABELS[arm]} {passed}/{runs}" for arm, passed, runs in item["order"]
        )
        spread = lead["spread_runs"][item["task_family"]]
        unit = "run" if spread == 1 else "runs"
        lines.append(f"| `{item['task_family']}` | {spread} {unit} | {order} |")
    lines += [
        "",
        "A family counts as discriminating here only if its best and worst arms "
        f"differ by at least {lead['minimum_spread_runs']} runs out of eight. One "
        "run of separation is not an ordering, and treating it as one "
        "manufactures reversals out of noise.",
        "",
        "## Does any language lead everywhere?",
        "",
    ]
    if lead["flat_families"]:
        flat = ", ".join(f"`{name}`" for name in lead["flat_families"])
        lines += [
            f"{flat} is flat across the arms by that test and contributes no",
            "correctness signal, so the question is answered by the two families",
            "carried over from v0.8.",
            "",
        ]
    if lead["best_on_every_discriminating_family"]:
        winners = ", ".join(
            LABELS[arm] for arm in lead["best_on_every_discriminating_family"]
        )
        lines += [
            f"{winners} is top on every family that discriminates in this cohort.",
            "",
        ]
    else:
        lines += [
            "No. No language is top on both families that discriminate, and none",
            "is bottom on both. The v0.8 disagreement reproduced in the sense that",
            "the two families still disagree.",
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
    if report["cohort_drift"]:
        lines += [
            "## How much the ordering moved since v0.8",
            "",
            "Same tasks, same model, same scaffold, same eight attempts per cell,",
            "a different randomization seed. This is the most useful number in the",
            "report, because it bounds how much weight any single ordering can",
            "carry.",
            "",
            "| Family | Arm | v0.8 | v0.9 | Change |",
            "|---|---|---:|---:|---:|",
        ]
        for item in report["cohort_drift"]:
            lines.append(
                f"| {item['task_family']} | {LABELS[item['language']]} | "
                f"{item['v08_passed']}/{item['v08_runs']} | "
                f"{item['v09_passed']}/{item['v09_runs']} | "
                f"{item['change_runs']:+d} |"
            )
        biggest = max(report["cohort_drift"], key=lambda item: abs(item["change_runs"]))
        lines += [
            "",
            f"The largest single move is {LABELS[biggest['language']]} on "
            f"`{biggest['task_family']}`, {biggest['change_runs']:+d} runs out of "
            "eight, with nothing changed but the seed. Eight attempts per cell is",
            "not enough to fix a per-family ordering, and any reading of these",
            "tables that treats the exact order as stable is reading noise. What",
            "survives across both cohorts is the weaker and more useful claim:",
            "the families disagree, and no arm leads on all of them.",
            "",
        ]
    lines += [
        "## Counting the offsets in the wrong unit",
        "",
        "Two `text-redact` hidden cases fail specifically when the offsets are",
        "counted in UTF-16 code units or bytes rather than code points:",
        "`code-point-offsets` and `astral-mask`. Every other failure mode leaves",
        "them alone. This is the mechanism the family was built to expose, and it",
        "did not appear once.",
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
        "the starter fails ten of the twelve checks. That is not the same as",
        "landing in the 40 to 60 percent band the design targets, and it did not.",
        "The result is reported as it came out rather than adjusted afterwards,",
        "and the forty rollouts it cost are the price of finding out. The design",
        "already says difficulty and model tier have to be calibrated jointly; a",
        "green gate is necessary and is plainly not sufficient.",
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
        "--schedule", type=pathlib.Path, default=ROOT / "studies" / "study_v0.9_luna_schedule.json"
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
