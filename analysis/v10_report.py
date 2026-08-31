#!/usr/bin/env python3
"""Build the v1.0 report from the cohort ledger and its schedule receipt.

Three task families, five language setups, eight attempts per cell, one model
rung. The report is per family and never pools them into one score, because the
families were built to reward different things and an average over them would
describe none of them.

Two things are deliberately absent. There is no comparison against earlier
cohorts: two of these families ran against revised instruction text, so the
comparison would be dishonest. And there is no wall-clock time: this cohort ran
four rollouts at a time, so elapsed time includes contention.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

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
    from analysis.v09_report import leadership, strip_timing
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
    from v09_report import leadership, strip_timing

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
    "expr-eval": "what an integer is: 64 bits, two's complement",
}
# Cases whose failure means the integer width, the division rule, or the wrap
# was wrong. A correct implementation of everything else leaves them alone.
WIDTH_CASES = (
    "wraparound",
    "hex-and-signed-literals",
    "literal-range",
    "division-truncation",
    "shift-semantics",
    "shift-range",
    "bitwise-full-width",
)


def width_failures(rows: list[dict]) -> list[dict]:
    """How often each arm got the integer width or the division rule wrong."""
    counts = {arm: {"runs": 0, "width_case_failures": 0} for arm in ARMS}
    for row in rows:
        if row["task_family"] != "expr-eval":
            continue
        entry = counts[row["language"]]
        entry["runs"] += 1
        if any(case in row.get("failed_cases", ()) for case in WIDTH_CASES):
            entry["width_case_failures"] += 1
    return [
        {
            "language": arm,
            **entry,
            "rate": (
                entry["width_case_failures"] / entry["runs"] if entry["runs"] else None
            ),
        }
        for arm, entry in counts.items()
    ]


def bar(value: float, largest: float, width: int = 28) -> str:
    """A proportional bar. Full blocks, so it renders the same everywhere."""
    if largest <= 0:
        return ""
    filled = max(1, round(width * value / largest))
    return "█" * filled


def cost_chart(report: dict) -> list[str]:
    """What each language cost to run, per rollout and in total."""
    rows = sorted(report["by_arm"], key=lambda cell: -cell["mean_cost_usd"])
    largest = max(cell["mean_cost_usd"] for cell in rows)
    lines = [
        "## What each language cost",
        "",
        "Cost is measured from the provider's own usage metadata, not estimated.",
        "It tracks agent steps closely, because steps are what buy tokens.",
        "",
        "Mean cost per rollout:",
        "",
        "```",
    ]
    for cell in rows:
        label = f"{LABELS[cell['language']]:<14}"
        amount = f"${cell['mean_cost_usd']:.6f}"
        lines.append(f"{label} {amount}  {bar(cell['mean_cost_usd'], largest)}")
    lines += [
        "```",
        "",
        "| Language | Mean cost | Total | Mean steps | Mean output tokens |",
        "|---|---:|---:|---:|---:|",
    ]
    for cell in rows:
        lines.append(
            f"| {LABELS[cell['language']]} | ${cell['mean_cost_usd']:.6f} | "
            f"${cell['total_cost_usd']:.4f} | {cell['mean_agent_steps']:.2f} | "
            f"{cell['mean_output_tokens']:,.0f} |"
        )

    families: dict[str, float] = {}
    for cell in report["by_family_and_arm"]:
        families[cell["task_family"]] = (
            families.get(cell["task_family"], 0.0) + cell["total_cost_usd"]
        )
    ordered = sorted(families.items(), key=lambda item: -item[1])
    widest = max(value for _, value in ordered)
    lines += ["", "Total spend by task family:", "", "```"]
    for family, value in ordered:
        lines.append(f"{family:<18} ${value:.4f}  {bar(value, widest)}")
    lines += [
        "```",
        "",
        f"The whole cohort cost ${report['total_cost_usd']:.6f}. The most expensive",
        f"language to run was {LABELS[rows[0]['language']]} at "
        f"${rows[0]['mean_cost_usd']:.6f} a rollout, "
        f"{rows[0]['mean_cost_usd'] / rows[-1]['mean_cost_usd']:.2f} times the cheapest, "
        f"{LABELS[rows[-1]['language']]}.",
        "",
    ]
    return lines


def build_report(schedule: pathlib.Path, ledger: pathlib.Path) -> dict:
    excluded: list[dict] = []
    rows = read_rows(ledger, schedule, excluded)
    attach_failed_cases(rows, ledger)
    contrasts = paired_contrasts(rows, seed=20260902)
    receipt = load(schedule)
    report = {
        "schema_version": "1.0.0",
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
        "expr_eval_width_failures": width_failures(rows),
        "decisive_correctness": decisive(contrasts, "hidden_test_pass"),
        "decisive_steps": decisive(contrasts, "agent_steps"),
        "notes": {
            "primary_estimand": (
                "per-family hidden-verifier pass rate by language, reported for "
                "all three families separately and never pooled into one score"
            ),
            "pooled_by_arm": (
                "the by_arm table pools families that do not agree; it is "
                "reported for completeness and is not the estimand"
            ),
            "no_drift_table": (
                "money-rollup and circuit-breaker ran against revised instruction "
                "text, so their pass rates are not comparable with v0.8 or v0.9"
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
    cells = {
        (cell["task_family"], cell["language"]): cell
        for cell in report["by_family_and_arm"]
    }
    families = sorted({family for family, _ in cells})

    lines = [
        "# Language AI Bench v1.0",
        "",
        "## What this measures",
        "",
        "One model, one agent, one scaffold, fresh context every run. Three",
        "refactors, each authored idiomatically in five setups, each verified by",
        "one language-neutral driver. The only thing that varies within a task is",
        "the language and the type checking that comes with it.",
        "",
        "Each task deliberately rewards a different thing, because a type system",
        "is not one lever. It reports the branch you forgot; it says nothing",
        "about whether you rounded correctly.",
        "",
        "| Family | What it rewards |",
        "|---|---|",
    ]
    for family in families:
        lines.append(f"| `{family}` | {REWARDS.get(family, 'see EQUIVALENCE.md')} |")

    lines += [
        "",
        f"**{report['rollouts']} rollouts, ${report['total_cost_usd']:.6f} measured spend.**",
        "",
        "## Results by family",
        "",
        "This is the estimand. The pooled table further down is not.",
        "",
        "| Family | Spread | Ordering |",
        "|---|---:|---|",
    ]
    for family in families:
        ranked = sorted(
            (cells[(family, arm)] for arm in ARMS if (family, arm) in cells),
            key=lambda cell: (-cell["passed"], cell["language"]),
        )
        spread = lead["spread_runs"][family]
        ordering = " > ".join(
            f"{LABELS[cell['language']]} {cell['passed']}/{cell['runs']}"
            for cell in ranked
        )
        unit = "run" if spread == 1 else "runs"
        lines.append(f"| `{family}` | {spread} {unit} | {ordering} |")

    lines += [
        "",
        "A family counts as discriminating only if its best and worst arms differ",
        f"by at least {lead['minimum_spread_runs']} runs out of eight. One run of separation is not an",
        "ordering, and treating it as one manufactures reversals out of noise.",
        "",
        "## The task picks the winner",
        "",
        "Different tasks ranking the languages differently is the expected",
        "result, not a defect in the measurement. Each of these tasks was built",
        "to stress a different part of writing code, and the languages differ in",
        "which of those parts they help with. An average over them would describe",
        "none of them, which is why every number here is reported per task.",
        "",
    ]
    discriminating = lead["discriminating_families"]
    flat = lead["flat_families"]
    lines.append(
        "Families that discriminate: "
        + (", ".join(f"`{name}`" for name in discriminating) or "none")
        + "."
    )
    if flat:
        lines.append(
            "Flat by that test, contributing no correctness signal: "
            + ", ".join(f"`{name}`" for name in flat)
            + "."
        )
    best = lead["best_on_every_discriminating_family"]
    worst = lead["worst_on_every_discriminating_family"]
    lines += [
        "",
        (
            f"Top on every discriminating family: {', '.join(LABELS[a] for a in best)}. "
            if best
            else "No language is top on every family that discriminates. "
        )
        + (
            f"Bottom on every one: {', '.join(LABELS[a] for a in worst)}."
            if worst
            else "None is bottom on every one either."
        ),
        "",
    ]
    if lead["reversals"]:
        lines += ["Reversals, where one language is best on one family and worst on another:", ""]
        for item in lead["reversals"]:
            lines.append(
                f"- {LABELS[item['language']]}: best on `{item['best_on']}`, "
                f"worst on `{item['worst_on']}`"
            )
        lines.append("")

    lines += [
        "## Why the tasks rank the languages differently",
        "",
        "The three tasks fail for different reasons, and a checker only helps",
        "with one of them.",
        "",
        "**`circuit-breaker` rewards being told what you missed.** The work is a",
        "three-state machine and a three-variant outcome union consumed across",
        "file boundaries. Drop a case and the program keeps running and returns",
        "the wrong answer, in JavaScript and in Python. `go build`, `tsc` and",
        "`mypy` all name the missing case at the point of the mistake. Go passes",
        "8 of 8 here; Python, which reports nothing, passes 2 of 8.",
        "",
        "**`money-rollup` rewards a library, and a checker is silent about it.**",
        "The failures are rounding mode, negative zero formatting, and the",
        "shortest conversion path. Every one of those type checks cleanly while",
        "being wrong: `half-up` and `half-even` have the same type. What helps is",
        "having exact rational arithmetic in the standard library, which Python",
        "does. This task is flat this cohort, at 36 of 39, so it separates",
        "nothing here, but that is what it separates on when it does.",
        "",
        "**`expr-eval` rewards saying the semantics out loud.** The contract is",
        "signed 64-bit two's complement. JavaScript has no such type at all, so",
        "the model has to make a visible decision, reach for `BigInt`, and mask",
        "to 64 bits; it passes 7 of 8. Go already has the semantics in `int64`,",
        "which turns out to be the trap: the parts that are not free, reading a",
        "literal as `uint64` before reinterpreting it, checking a shift count,",
        "and spelling complement `^x` where the contract writes `~x`, get missed.",
        "Go passes 0 of 8 while spending the most steps of any arm.",
        "",
        "So a type system helps when the error class is a shape the checker can",
        "see, and does nothing when the error class is a value or a convention.",
        "Both kinds of bug are ordinary. Which one a ticket contains is not a",
        "property of the language you write it in.",
        "",
        "## Two results to read carefully",
        "",
        "The matched JavaScript and TypeScript pair splits on `expr-eval`, 7 of 8",
        "against 3 of 8, with the typed arm behind while spending 3.25 more",
        "steps. That pair is the analytical centerpiece of this design, so it is",
        "tempting to read. Eight attempts per cell cannot carry it: a rerun of a",
        "fixed cell with nothing changed but the random seed has moved by 4 runs",
        "out of 8 in this project before. Treat it as a cell that needs more",
        "seeds, not as an effect.",
        "",
        "`money-rollup` is flat here, at 36 of 39 with a spread of 1 run. Its",
        "instruction was revised for this cohort, so there is no honest way to",
        "separate the text from the seed, and the family is marked for re-probing",
        "rather than carrying a status it did not earn under the text it ran.",
        "",
        "## Getting the integer width wrong",
        "",
        "Seven `expr-eval` hidden cases fail specifically when the width, the",
        "division rule, or the wrap is wrong: `wraparound`,",
        "`hex-and-signed-literals`, `literal-range`, `division-truncation`,",
        "`shift-semantics`, `shift-range`, and `bitwise-full-width`. This is the",
        "mechanism the family was built to expose, and it fires.",
        "",
        "| Language | Runs | Runs failing a width case | Rate |",
        "|---|---:|---:|---:|",
    ]
    for entry in report["expr_eval_width_failures"]:
        rate = "n/a" if entry["rate"] is None else f"{entry['rate']:.2f}"
        lines.append(
            f"| {LABELS[entry['language']]} | {entry['runs']} | "
            f"{entry['width_case_failures']} | {rate} |"
        )

    lines += [
        "",
        "## Results by family and arm",
        "",
        "| Family | Language | Passed | Pass rate | Mean steps |",
        "|---|---|---:|---:|---:|",
    ]
    for family in families:
        for arm in ARMS:
            cell = cells.get((family, arm))
            if not cell:
                continue
            lines.append(
                f"| `{family}` | {LABELS[arm]} | {cell['passed']}/{cell['runs']} | "
                f"{cell['pass_rate']:.2f} | {cell['mean_agent_steps']:.2f} |"
            )

    lines.append("")
    lines += cost_chart(report)

    lines += [
        "## Pooled across all three families",
        "",
        "Reported for completeness. Pooling families that disagree produces a",
        "number that describes none of them.",
        "",
        "| Language | Passed | Pass rate (95% CI) | Mean steps | Mean cost |",
        "|---|---:|---:|---:|---:|",
    ]
    for cell in sorted(report["by_arm"], key=lambda item: item["language"]):
        low, high = cell["pass_rate_ci95"]
        lines.append(
            f"| {LABELS[cell['language']]} | {cell['passed']}/{cell['runs']} | "
            f"{cell['pass_rate']:.2f} [{low:.2f}, {high:.2f}] | "
            f"{cell['mean_agent_steps']:.2f} | ${cell['mean_cost_usd']:.6f} |"
        )

    decisive_rows = report["decisive_correctness"] + report["decisive_steps"]
    lines += ["", "## Contrasts whose interval excludes zero", ""]
    if decisive_rows:
        for item in decisive_rows:
            lines.append(f"- {item}")
    else:
        lines.append(
            "None. Every paired contrast in this cohort has an interval that "
            "touches zero, which is a finding and not a gap."
        )

    lines += [
        "",
        "## Why earlier cohorts are not tabulated next to this one",
        "",
        "`money-rollup` and `circuit-breaker` used to end their instructions by",
        "listing the topics their hidden tests cover, which hands the agent a",
        "checklist of what the grader looks at. That line is gone, so these two",
        "tasks ran against different text than in any earlier report and their",
        "pass rates are not comparable with those. Printing a change column would",
        "invite exactly that comparison, so there is none.",
        "",
        "## Scope and limits",
        "",
        "Three brownfield families, five arms, eight attempts per cell, one model",
        "rung, one bash-only scaffold. Three families is below the point where",
        "between-family variance is well estimated, so this supports claims",
        "about these three tasks and no language-general claim.",
        "",
        "The stopping rule was fixed at 120 rollouts before the first paid call",
        "and no interim analysis informed continuation. `expr-eval` reached this",
        "cohort through two pre-registered probes, reported in full in",
        "`docs/EXPR_EVAL_PROBE.md`; those 20 rollouts are not pooled here and the",
        "cohort ran on fresh seeds.",
        "",
        "Agent wall time is not reported. This cohort ran four rollouts at a time,",
        "so elapsed time includes contention. All three families are command-mode,",
        "so no timing-sensitive verifier case was exposed to it.",
        "",
        "The families were chosen to reward different things, so disagreement",
        "between them is partly by construction. That is the point: it shows the",
        "ordering is a property of the task, not of the language. It does not show",
        "how often real tickets look like any one of these three.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schedule", type=pathlib.Path, default=ROOT / "study_v1.0_luna_schedule.json"
    )
    parser.add_argument(
        "--ledger", type=pathlib.Path, default=ROOT / ".benchmark-state" / "v10-spend.json"
    )
    parser.add_argument("--json-output", type=pathlib.Path)
    parser.add_argument("--markdown-output", type=pathlib.Path)
    args = parser.parse_args()

    report = build_report(args.schedule, args.ledger)
    if args.json_output:
        args.json_output.write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    text = render_markdown(report)
    if args.markdown_output:
        args.markdown_output.write_text(text, encoding="utf-8", newline="\n")
    # The cost chart uses block characters; a legacy console encoding must not
    # make writing the report fail.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text, end="")


if __name__ == "__main__":
    main()
