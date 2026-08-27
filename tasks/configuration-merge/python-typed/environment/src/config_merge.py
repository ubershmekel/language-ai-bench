import json
import sys
from typing import Any, cast

JsonObject = dict[str, Any]
Layers = dict[str, JsonObject]

LAYERS = ("defaults", "file", "env", "cli")


def validate(value: object) -> Layers:
    keys = set(LAYERS)
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("invalid input")
    if any(not isinstance(value[key], dict) for key in keys):
        raise ValueError("invalid layer")
    return cast(Layers, value)


def merge(value: object) -> JsonObject:
    layers = validate(value)
    result: JsonObject = {}
    for key in LAYERS:
        result.update(layers[key])
    return result


try:
    print(json.dumps(merge(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
