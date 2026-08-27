import json
import sys
from typing import Any, TypedDict

from breaker import admit, new_breaker, observe, record
from parse import Recorded, State, classify, parse_config, parse_document


class Decision(TypedDict):
    target: str
    state: State
    admitted: bool
    recorded: Recorded


class Summary(TypedDict):
    target: str
    state: State
    failures: int


class Result(TypedDict):
    decisions: list[Decision]
    targets: list[Summary]


def run(value: object) -> Result:
    document = parse_document(value)
    config = parse_config(document["config"])
    breaker = new_breaker()
    seen: list[str] = []
    decisions: list[Decision] = []
    for call in document["calls"]:
        target = call["target"]
        if target not in seen:
            seen.append(target)
        observed = observe(breaker, call["at"], config)
        if not admit(breaker, observed, config):
            decisions.append(
                {
                    "target": target,
                    "state": observed,
                    "admitted": False,
                    "recorded": "rejected",
                }
            )
            continue
        outcome = classify(call["outcome"], config["failureStatuses"])
        record(breaker, observed, outcome, call["at"], config)
        decisions.append(
            {
                "target": target,
                "state": observed,
                "admitted": True,
                "recorded": outcome,
            }
        )
    return {
        "decisions": decisions,
        "targets": [
            {
                "target": name,
                "state": breaker["state"],
                "failures": breaker["failures"],
            }
            for name in seen
        ],
    }


try:
    print(json.dumps(run(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
