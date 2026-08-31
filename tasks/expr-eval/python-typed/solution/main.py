"""Read one JSON document, evaluate every program, and report the results."""

import json
import sys
from typing import Any, Dict, List

from evaluate import evaluate
from parse import ProgramError, parse_document, parse_program


def run(value: Any) -> Dict[str, Any]:
    document = parse_document(value)
    results: List[Dict[str, Any]] = []
    failed = 0
    for program in document.programs:
        try:
            parsed = parse_program(program.source, document.max_depth)
            results.append({"id": program.id, "value": evaluate(parsed)})
        except ProgramError as error:
            failed += 1
            results.append(
                {"id": program.id, "error": {"code": error.code, "at": error.at}}
            )
    return {
        "results": results,
        "stats": {"programs": len(document.programs), "failed": failed},
    }


def main() -> int:
    try:
        document = json.loads(sys.stdin.read())
        sys.stdout.write(json.dumps(run(document)) + "\n")
    except Exception as error:  # noqa: BLE001
        sys.stderr.write(f"{error}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
