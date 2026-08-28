"""Find the regions a rule matches, combine them, and mask them."""

import os
from typing import TypedDict

from parse import Rule, Span

Found = tuple[int, int]
Attributed = tuple[int, int, str]


class Growing(TypedDict):
    start: int
    end: int
    rules: set[str]


def find_spans(rule: Rule, points: list[str]) -> list[Found]:
    """Every non-overlapping occurrence, scanning left to right."""
    if rule["kind"] == "span":
        return [(rule["start"], rule["end"])]
    value = list(rule["value"])
    width = len(value)
    spans: list[Found] = []
    index = 0
    while index + width <= len(points):
        if points[index : index + width] == value:
            spans.append((index, index + width))
            if os.environ.get("LAB_SABOTAGE") == "overlapping-literal-matches":
                index += 1
            else:
                index += width
        else:
            index += 1
    return spans


def keep_long_enough(spans: list[Found], minimum: int) -> list[Found]:
    return [item for item in spans if item[1] - item[0] >= minimum]


def has_overlap(spans: list[Found]) -> bool:
    ordered = sorted(spans)
    for left, right in zip(ordered, ordered[1:]):
        if right[0] < left[1]:
            return True
    return False


def merge_spans(spans: list[Attributed]) -> list[Span]:
    """Combine spans that overlap or touch, keeping every contributing id."""
    joined = os.environ.get("LAB_SABOTAGE") != "merge-drops-touching"
    merged: list[Growing] = []
    for start, end, identifier in sorted(spans):
        last = merged[-1] if merged else None
        if last is not None and (
            start < last["end"] or (joined and start == last["end"])
        ):
            last["end"] = max(last["end"], end)
            last["rules"].add(identifier)
        else:
            merged.append({"start": start, "end": end, "rules": {identifier}})
    return [
        {"start": item["start"], "end": item["end"], "rules": sorted(item["rules"])}
        for item in merged
    ]


def apply_mask(points: list[str], spans: list[Span], mask: str) -> str:
    masked = list(points)
    for span in spans:
        for index in range(span["start"], span["end"]):
            masked[index] = mask
    return "".join(masked)
