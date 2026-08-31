"""Read one JSON document, evaluate every program, and report the results."""

import json
import sys

from evaluate import evaluate
from parse import parse_document, tokenize


def run(value):
    document = parse_document(value)
    results = []
    for program in document["programs"]:
        tokens = tokenize(program["source"])
        results.append({"id": program["id"], "value": evaluate(tokens)})
    return {
        "results": results,
        "stats": {"programs": len(results), "failed": 0},
    }


def main():
    try:
        document = json.loads(sys.stdin.read())
        sys.stdout.write(json.dumps(run(document)) + "\n")
    except Exception as error:  # noqa: BLE001
        sys.stderr.write(f"{error}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
