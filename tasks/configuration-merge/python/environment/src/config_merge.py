import json
import sys


def validate(value):
    keys = {"defaults", "file", "env", "cli"}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("invalid input")
    if any(not isinstance(value[key], dict) for key in keys):
        raise ValueError("invalid layer")


def merge(value):
    validate(value)
    result = {}
    for key in ("defaults", "file", "env", "cli"):
        result.update(value[key])
    return result


try:
    print(json.dumps(merge(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
