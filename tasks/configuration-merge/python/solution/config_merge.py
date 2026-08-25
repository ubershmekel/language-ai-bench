import copy
import json
import os
import sys


def validate(value):
    keys = {"defaults", "file", "env", "cli"}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("invalid input")
    if any(not isinstance(value[key], dict) for key in keys):
        raise ValueError("invalid layer")


def merge_into(target, layer, sabotage):
    for key, value in layer.items():
        if value is None and sabotage != "ignore-delete":
            target.pop(key, None)
        elif isinstance(value, dict) and sabotage != "shallow-merge":
            base = target.get(key)
            target[key] = merge_into(copy.deepcopy(base) if isinstance(base, dict) else {}, value, sabotage)
        elif isinstance(value, list) and sabotage == "merge-arrays" and isinstance(target.get(key), list):
            target[key] = copy.deepcopy(target[key]) + copy.deepcopy(value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def merge(value):
    validate(value)
    sabotage = os.environ.get("LAB_SABOTAGE", "")
    layers = [value[key] for key in ("defaults", "file", "env", "cli")]
    if sabotage == "reverse-precedence":
        layers.reverse()
    result = {}
    for layer in layers:
        merge_into(result, layer, sabotage)
    return result


try:
    print(json.dumps(merge(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
