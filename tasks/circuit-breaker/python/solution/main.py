import json
import os
import sys

from breaker import admit, new_breaker, observe, record
from parse import classify, parse_call, parse_config, parse_document


def run(value):
    document = parse_document(value)
    config = parse_config(document["config"])
    breakers = {}
    decisions = []
    previous = 0
    for item in document["calls"]:
        at, target, raw = parse_call(item, previous)
        previous = at
        outcome = classify(raw, config["failureStatuses"])
        key = "" if os.environ.get("LAB_SABOTAGE") == "global-state" else target
        if key not in breakers:
            breakers[key] = new_breaker()
        breaker = breakers[key]
        observed = observe(breaker, at, config)
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
        record(breaker, observed, outcome, at, config)
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
            for name, breaker in sorted(breakers.items())
        ],
    }


try:
    print(json.dumps(run(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
