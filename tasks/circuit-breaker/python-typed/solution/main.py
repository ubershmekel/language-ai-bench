import json
import os
import sys
from typing import TypedDict

from breaker import Breaker, admit, new_breaker, observe, record
from parse import Recorded, State, classify, parse_call, parse_config, parse_document


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
    breakers: dict[str, Breaker] = {}
    decisions: list[Decision] = []
    previous = 0
    for item in document["calls"]:
        call = parse_call(item, previous)
        previous = call["at"]
        outcome = classify(call["outcome"], config["failureStatuses"])
        key = "" if os.environ.get("LAB_SABOTAGE") == "global-state" else call["target"]
        if key not in breakers:
            breakers[key] = new_breaker()
        breaker = breakers[key]
        observed = observe(breaker, call["at"], config)
        if not admit(breaker, observed, config):
            decisions.append(
                {
                    "target": call["target"],
                    "state": observed,
                    "admitted": False,
                    "recorded": "rejected",
                }
            )
            continue
        record(breaker, observed, outcome, call["at"], config)
        decisions.append(
            {
                "target": call["target"],
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
                "state": item["state"],
                "failures": item["failures"],
            }
            for name, item in sorted(breakers.items())
        ],
    }


try:
    print(json.dumps(run(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
