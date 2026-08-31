#!/usr/bin/env python3
"""Build the v1.0 report: three families that all discriminate, at one revision.

v0.8 and v0.9 both ended with the same shape of result. `money-rollup` and
`circuit-breaker` rank the five arms in nearly opposite orders, and each
ordering follows from the affordance that family rewards. The third family in
each cohort could not break the tie: `text-redact` saturated at 39 of 40 with
its hazard never firing, and `redact-spans`, the same contract with every
signpost removed, then probed 10 of 10.

v1.0's third family is `expr-eval`, which turns on what an integer is. It is
also the first family built to a different size: an eight line ticket over a
SPEC.md in the workspace, against a reference that is a tokenizer, a parser and
an evaluator. It was admitted by a pre-registered probe at 4 of 10 after a first
probe at 0 of 10, and both probes are reported in docs/EXPR_EVAL_PROBE.md.

There is no drift table in this report. `money-rollup` and `circuit-breaker` no
longer end their instructions by listing the topics their hidden tests cover, so
their numbers here are measured against different text than v0.8 and v0.9 and
the comparison would be dishonest.

Agent wall time is deliberately absent. This cohort ran four rollouts at a time.
"""

from __future__ import annotations

import argparse
import json
import pathlib

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
        "# Language AI Bench v1.0: a family sized like a real ticket",
        "",
        "## What this cohort was for",
        "",
        "Two cohorts in a row ended with two families that discriminate and a",
        "third that could not. `text-redact` saturated at 39 of 40 with its code",
        "point hazard never firing once, and `redact-spans`, the same contract",
        "with every signpost stripped out and more hidden cases able to catch a",
        "wrong unit, then passed 10 of 10 on a probe. Hiding a hazard inside a",
        "small task does not make the task hard.",
        "",
        "So `expr-eval` moves the size instead. Its ticket is eight lines and",
        "points at a `SPEC.md` in the workspace; its reference is a tokenizer, a",
        "precedence climbing parser, and an evaluator. That is the shape the",
        "DeepSWE comparison has pointed at since v0.7: their median instruction",
        "is 15 lines over an 844 line patch, against 69 to 82 lines over about",
        "300 here.",
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
        f"by at least {lead['minimum_spread_runs']} runs out of eight, the same bar v0.9 used. One run",
        "of separation is not an ordering.",
        "",
        "## Does any language lead everywhere?",
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
        "## What the new family bought",
        "",
        "`expr-eval` is the first third family in three cohorts that separates",
        "the arms, and it separates them further than either of the families it",
        "was added to: a spread of 7 runs out of 8, against 6 for",
        "`circuit-breaker`. It also produces the cleanest reversal this repo has",
        "measured. Go passes every `circuit-breaker` rollout and none of the",
        "`expr-eval` ones. Both orderings follow from what the family rewards, so",
        "neither is a fact about Go.",
        "",
        "Go's failure is worth stating precisely, because the obvious reading is",
        "wrong. Go is the arm that gets the contract's arithmetic for free:",
        "`int64` wraps, `/` truncates toward zero, `>>` propagates the sign. What",
        "it does not get for free is everything around that, and that is where it",
        "failed: reading a literal as `uint64` before reinterpreting it, checking",
        "a shift count, and spelling bitwise complement `^x` where the contract",
        "writes `~x`. Go rollouts also worked hardest, at 13.25 steps against",
        "8.25 for JavaScript, and still finished at zero. Having the semantics",
        "built into the language did not help; having to say them out loud is a",
        "different skill.",
        "",
        "The matched JavaScript and TypeScript pair splits here, 7 of 8 against 3",
        "of 8, and the typed arm is the one that does worse while spending 3.25",
        "more steps. Eight attempts per cell cannot carry that as a finding, and",
        "v0.9 measured a single-seed swing of 4 runs out of 8 on a fixed cell, so",
        "read it as a cell worth more seeds rather than as an effect.",
        "",
        "`money-rollup` went flat, at 36 of 39 with a spread of 1 run, after",
        "discriminating in both v0.8 and v0.9. Its instruction changed in this",
        "revision, so there is no honest way to attribute that here, and it is",
        "the reason a family needs re-probing after its text changes rather than",
        "an inherited status.",
        "",
        "## Getting the integer width wrong",
        "",
        "Seven `expr-eval` hidden cases fail specifically when the width, the",
        "division rule, or the wrap is wrong: `wraparound`,",
        "`hex-and-signed-literals`, `literal-range`, `division-truncation`,",
        "`shift-semantics`, `shift-range`, and `bitwise-full-width`. This is the",
        "mechanism the family was built to expose, and unlike v0.9's code point",
        "hazard it does fire.",
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

    lines += [
        "",
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
        "## Why there is no drift table",
        "",
        "v0.9 carried one, comparing each family against v0.8 with nothing",
        "changed but the seed, and it was the most useful number in that report:",
        "the largest single move was 4 runs out of 8.",
        "",
        "This cohort cannot carry one. `money-rollup` and `circuit-breaker` used",
        "to end their instructions by listing the topics their hidden tests",
        "cover, which hands the agent a checklist of what the grader looks at.",
        "That line is gone as of task text revision v1.0, so these two families",
        "ran against different text than they did in v0.8 and v0.9. Their pass",
        "rates here are not comparable with those cohorts, and printing a change",
        "column would invite exactly that comparison.",
        "",
        "## Scope and limits",
        "",
        "Three brownfield families, five arms, eight attempts per cell, one model",
        "rung, one bash-only scaffold. Three families is still below the point",
        "where between-family variance is well estimated, so this supports claims",
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
    print(text, end="")


if __name__ == "__main__":
    main()
