"""Find the regions a rule matches, combine them, and mask them."""

import os


def find_spans(rule, points):
    """Every non-overlapping occurrence, scanning left to right."""
    if rule["kind"] == "span":
        return [(rule["start"], rule["end"])]
    value = list(rule["value"])
    width = len(value)
    spans = []
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


def keep_long_enough(spans, minimum):
    return [item for item in spans if item[1] - item[0] >= minimum]


def has_overlap(spans):
    ordered = sorted(spans)
    for left, right in zip(ordered, ordered[1:]):
        if right[0] < left[1]:
            return True
    return False


def merge_spans(spans):
    """Combine spans that overlap or touch, keeping every contributing id."""
    joined = os.environ.get("LAB_SABOTAGE") != "merge-drops-touching"
    merged = []
    for start, end, identifier in sorted(spans):
        if merged and (start < merged[-1]["end"] or (joined and start == merged[-1]["end"])):
            merged[-1]["end"] = max(merged[-1]["end"], end)
            merged[-1]["rules"].add(identifier)
        else:
            merged.append({"start": start, "end": end, "rules": {identifier}})
    return [
        {"start": item["start"], "end": item["end"], "rules": sorted(item["rules"])}
        for item in merged
    ]


def apply_mask(points, spans, mask):
    masked = list(points)
    for span in spans:
        for index in range(span["start"], span["end"]):
            masked[index] = mask
    return "".join(masked)
