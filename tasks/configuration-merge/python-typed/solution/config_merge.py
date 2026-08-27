import copy
import json
import os
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


def merge_into(target: JsonObject, layer: JsonObject, sabotage: str) -> JsonObject:
    for key, value in layer.items():
        if value is None and sabotage != "ignore-delete":
            target.pop(key, None)
        elif isinstance(value, dict) and sabotage != "shallow-merge":
            base = target.get(key)
            target[key] = merge_into(
                copy.deepcopy(base) if isinstance(base, dict) else {}, value, sabotage
            )
        elif (
            isinstance(value, list)
            and sabotage == "merge-arrays"
            and isinstance(target.get(key), list)
        ):
            target[key] = copy.deepcopy(target[key]) + copy.deepcopy(value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def merge(value: object) -> JsonObject:
    validated = validate(value)
    sabotage = os.environ.get("LAB_SABOTAGE", "")
    layers = [validated[key] for key in LAYERS]
    if sabotage == "reverse-precedence":
        layers.reverse()
    result: JsonObject = {}
    for layer in layers:
        merge_into(result, layer, sabotage)
    return result


try:
    print(json.dumps(merge(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
