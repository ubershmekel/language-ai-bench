#!/usr/bin/env python3
"""Report the redact-spans difficulty probe against its pre-registered rule.

This is not a cohort report. Ten rollouts cannot estimate a pass rate and this
script does not try to. It answers one question that was written down before the
first paid call: does redact-spans discriminate, and does it discriminate for
the reason it exists, meaning a wrong string unit rather than something else.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The hidden cases that a correct implementation counting UTF-16 code units or
# bytes instead of code points fails. Measured, not assumed: changing the one
# code point conversion in the JavaScript reference to text.split("") fails
# exactly these seven.
WRONG_UNIT_CASES = (
    "code-point-offsets",
    "astral-mask",
    "astral-literal-scan",
    "merge-touching",
    "min-length-drops-before-merge",
    "stats-and-order",
    "rejects-invalid",
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
        collected.append(
            {
                "order_index": run["order_index"],
                "language": run["language"],
                "attempt": run["attempt"],
                "reward": run["reward"],
                "passed": run["reward"] == 1,
                "cost_usd": run["cost_usd"],
                "exception_type": run.get("exception_type"),
                "failed_cases": failed,
                "wrong_unit": bool(set(failed) & set(WRONG_UNIT_CASES)),
            }
        )
    return collected


def render(collected: list[dict], study: dict) -> str:
    scored = [row for row in collected if not row["exception_type"]]
    passes = sum(1 for row in scored if row["passed"])
    wrong_unit = sum(1 for row in scored if row["wrong_unit"])
    spend = sum(row["cost_usd"] for row in collected)
    admitted = passes <= 7 and wrong_unit >= 1

    lines = [
        "# redact-spans difficulty probe",
        "",
        "Ten rollouts, two per language, at the same rung the cohorts use. This",
        "is a go/no-go on the task. It is not a cohort result, it estimates no",
        "pass rate, and it must never be pooled with one.",
        "",
        f"**{passes} of {len(scored)} passed. {wrong_unit} of {len(scored)} failed at "
        f"least one wrong-unit case. ${spend:.6f} measured spend.**",
        "",
        "## The pre-registered rule",
        "",
        "Written into the probe JSON before the first paid call and not touched",
        "since. It says text-redact v1.0 because it was written before the",
        "family was given its own id; it is this family.",
        "",
        study["admission_rule"],
        "",
        f"Verdict: **{'admit' if admitted else 'do not admit'}**.",
        "",
        "## By language",
        "",
        "| Language | Passed | Runs failing a wrong-unit case |",
        "|---|---:|---:|",
    ]
    for language in LABELS:
        subset = [row for row in scored if row["language"] == language]
        if not subset:
            continue
        lines.append(
            f"| {LABELS[language]} | {sum(1 for r in subset if r['passed'])}/"
            f"{len(subset)} | {sum(1 for r in subset if r['wrong_unit'])} |"
        )

    lines += ["", "## Failing verifier cases", "", "| Language | Failing cases |", "|---|---|"]
    for language in LABELS:
        counts: Counter[str] = Counter()
        for row in scored:
            if row["language"] == language:
                counts.update(row["failed_cases"])
        if not any(row["language"] == language for row in scored):
            continue
        rendered = ", ".join(f"{case} x{count}" for case, count in counts.most_common())
        lines.append(f"| {LABELS[language]} | {rendered or 'none'} |")

    lines += [
        "",
        "## What this rules out",
        "",
        "The v0.9 diagnosis was that the instruction telegraphed the hazard: it",
        "titled the task after the code point rule, gave the rule a paragraph of",
        "its own ending in a sentence saying it does not matter how your language",
        "indexes a string, and closed by naming the two hidden cases that catch a",
        "wrong unit. This family removes all of that, states the unit once where",
        "each field is defined, and adds three more hidden cases that a wrong unit",
        "breaks. Changing the one code point conversion in the JavaScript",
        "reference to text.split(\"\") now fails seven of the thirteen cases",
        "against four of twelve before.",
        "",
        "It made no difference. Every language passed twice, and no run failed a",
        "wrong-unit case. So the signposting was not what made v0.9 saturate. At",
        "this rung the model counts code points correctly in all five languages",
        "without being told to. Ten rollouts cannot put a number on how often it",
        "would slip, but they are enough to say that hiding the hazard better is",
        "not the lever. The mechanism is real and this model is not visibly",
        "vulnerable to it, which is a fact about the model, not a fault in the",
        "task.",
        "",
        "That leaves two honest options and one dishonest one. The task can be",
        "made larger, which is the lever the DeepSWE comparison already points",
        "at: their median reference patch is 844 lines against 301 here, and",
        "their median instruction is 15 lines against 69. Or the rung can move,",
        "which contradicts the selection ladder and buys a result about a weaker",
        "model. The dishonest option is to keep probing small variations until",
        "one lands under the threshold, which is fitting the task to a target and",
        "is not done here.",
        "",
        "`redact-spans` stays in the tree, gate green, unadmitted. It costs",
        "nothing to keep and it is the receipt for a claim worth having: the",
        "code point hazard does not discriminate at this rung.",
    ]

    excluded = [row for row in collected if row["exception_type"]]
    if excluded:
        lines += [
            "",
            "## Excluded",
            "",
            f"{len(excluded)} rollouts hit a Pier exception and are not scored.",
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=pathlib.Path, default=ROOT / "probe_redact_spans.json")
    parser.add_argument(
        "--schedule", type=pathlib.Path, default=ROOT / "probe_redact_spans_schedule.json"
    )
    parser.add_argument(
        "--ledger",
        type=pathlib.Path,
        default=ROOT / ".benchmark-state" / "probe-redact-spans-spend.json",
    )
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    text = render(rows(args.ledger, args.schedule), load(args.study))
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")


if __name__ == "__main__":
    main()
