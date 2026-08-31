#!/usr/bin/env python3
"""Report the expr-eval difficulty probes against their pre-registered rule.

Not a cohort report. Ten rollouts cannot estimate a pass rate and this script
does not try to. It answers the question that was written down before the first
paid call: does the family separate the arms, and does it separate them for the
reason it exists rather than for some other one.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The hidden cases that a wrong integer width, a wrong division rule, or a
# missing wrap breaks. Measured against the references, not assumed.
WIDTH_CASES = (
    "wraparound",
    "hex-and-signed-literals",
    "literal-range",
    "division-truncation",
    "shift-semantics",
    "shift-range",
    "bitwise-full-width",
)

LABELS = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "python-typed": "Python (typed)",
    "go": "Go",
}


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rows(ledger_path: pathlib.Path, schedule_path: pathlib.Path) -> list[dict]:
    ledger, receipt = load(ledger_path), load(schedule_path)
    planned = {row["order_index"]: row for row in receipt["schedule"]}
    collected = []
    for run in ledger.get("runs", []):
        plan = planned[run["order_index"]]
        for key in ("task_family", "language", "attempt", "sample_seed"):
            if plan[key] != run.get(key):
                raise SystemExit(f"ledger/schedule mismatch at {run['order_index']}")
        result = ROOT / run["result_path"]
        details = result.parent / "verifier" / "details.json"
        failed: list[str] = []
        if details.is_file():
            report = load(details)
            failed = [
                item["case_id"]
                for item in report.get("case_results", [])
                if not item["passed"]
            ]
        agent = load(result).get("agent_result") or {}
        collected.append(
            {
                "order_index": run["order_index"],
                "language": run["language"],
                "passed": run["reward"] == 1,
                "cost_usd": run["cost_usd"],
                "steps": agent.get("n_agent_steps"),
                "exception_type": run.get("exception_type"),
                "failed_cases": failed,
                "width": bool(set(failed) & set(WIDTH_CASES)),
            }
        )
    return collected


def summary(collected: list[dict]) -> dict:
    scored = [row for row in collected if not row["exception_type"]]
    return {
        "runs": len(scored),
        "passes": sum(1 for row in scored if row["passed"]),
        "width_failures": sum(1 for row in scored if row["width"]),
        "spend": sum(row["cost_usd"] for row in collected),
        "rows": scored,
    }


def render_probe(title: str, study: dict, collected: list[dict]) -> list[str]:
    data = summary(collected)
    admitted = 1 <= data["passes"] <= 7
    lines = [
        f"## {title}",
        "",
        f"**{data['passes']} of {data['runs']} passed. {data['width_failures']} of "
        f"{data['runs']} failed at least one integer-width case. "
        f"${data['spend']:.6f} measured spend.**",
        "",
        f"Verdict against the pre-registered rule: **{'admit' if admitted else 'do not admit'}**.",
        "",
        "| Language | Passed | Failed a width case | Median cases failed | Median steps |",
        "|---|---:|---:|---:|---:|",
    ]
    for language, label in LABELS.items():
        subset = [row for row in data["rows"] if row["language"] == language]
        if not subset:
            continue
        failures = sorted(len(row["failed_cases"]) for row in subset)
        steps = sorted(row["steps"] or 0 for row in subset)
        middle = len(subset) // 2
        lines.append(
            f"| {label} | {sum(1 for r in subset if r['passed'])}/{len(subset)} | "
            f"{sum(1 for r in subset if r['width'])} | {failures[middle]} | {steps[middle]} |"
        )

    counts: Counter[str] = Counter()
    for row in data["rows"]:
        counts.update(row["failed_cases"])
    lines += ["", "Cases by how many rollouts failed them:", "", "| Case | Rollouts |", "|---|---:|"]
    for case, count in counts.most_common():
        lines.append(f"| `{case}` | {count}/{data['runs']} |")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    probes = [
        (
            "First probe: 15 cases, two developer cases",
            ROOT / "probe_expr_eval.json",
            ROOT / "probe_expr_eval_schedule.json",
            ROOT / ".benchmark-state" / "probe-expr-eval-spend.json",
        ),
        (
            "Second probe: 20 cases, seven developer cases",
            ROOT / "probe_expr_eval_2.json",
            ROOT / "probe_expr_eval_2_schedule.json",
            ROOT / ".benchmark-state" / "probe-expr-eval-2-spend.json",
        ),
    ]

    lines = [
        "# expr-eval difficulty probes",
        "",
        "Ten rollouts each, two per language, at the same rung the cohorts use.",
        "These are go/no-go decisions on the task. They estimate no pass rate and",
        "must never be pooled with a cohort result.",
        "",
        "## The pre-registered rule",
        "",
        "Admit only if the family passes at most 7 of 10 and at least 1 of 10.",
        "The upper bound catches saturation, which is how `text-redact` and",
        "`redact-spans` failed. The lower bound catches a wall: a family every",
        "arm fails ranks nothing either.",
        "",
    ]
    for title, study_path, schedule_path, ledger_path in probes:
        if not ledger_path.is_file():
            continue
        lines += render_probe(title, load(study_path), rows(ledger_path, schedule_path))
        lines.append("")

    text = "\n".join(lines) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")


if __name__ == "__main__":
    main()
