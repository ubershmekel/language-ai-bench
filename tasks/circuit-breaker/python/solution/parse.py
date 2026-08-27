"""Validate the run description and classify call outcomes."""

import re

TOP_LEVEL = {"config", "calls"}
CONFIG_KEYS = {"threshold", "cooldownMs", "halfOpenLimit", "failureStatuses"}
CALL_KEYS = {"at", "target", "outcome"}
TARGET = re.compile(r"^[A-Za-z0-9_.-]+$")


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def is_status(value):
    return is_int(value) and 100 <= value <= 599


def parse_document(value):
    if not isinstance(value, dict) or set(value) != TOP_LEVEL:
        raise ValueError("malformed document")
    if not isinstance(value["calls"], list):
        raise ValueError("malformed calls")
    return value


def parse_config(value):
    if not isinstance(value, dict) or set(value) != CONFIG_KEYS:
        raise ValueError("malformed config")
    threshold = value["threshold"]
    cooldown = value["cooldownMs"]
    limit = value["halfOpenLimit"]
    statuses = value["failureStatuses"]
    if not is_int(threshold) or threshold < 1:
        raise ValueError("malformed threshold")
    if not is_int(cooldown) or cooldown < 0:
        raise ValueError("malformed cooldown")
    if not is_int(limit) or limit < 1:
        raise ValueError("malformed half-open limit")
    if not isinstance(statuses, list) or any(not is_status(item) for item in statuses):
        raise ValueError("malformed failure statuses")
    if len(set(statuses)) != len(statuses):
        raise ValueError("duplicate failure status")
    return {
        "threshold": threshold,
        "cooldownMs": cooldown,
        "halfOpenLimit": limit,
        "failureStatuses": set(statuses),
    }


def parse_call(value, previous):
    if not isinstance(value, dict) or set(value) != CALL_KEYS:
        raise ValueError("malformed call")
    at = value["at"]
    target = value["target"]
    if not is_int(at) or at < 0 or at < previous:
        raise ValueError("malformed timestamp")
    if not isinstance(target, str) or not TARGET.match(target):
        raise ValueError("malformed target")
    return at, target, value["outcome"]


def classify(outcome, failure_statuses):
    """Sort an outcome into a success, a failure, or a neutral result."""
    if not isinstance(outcome, dict) or "kind" not in outcome:
        raise ValueError("malformed outcome")
    kind = outcome["kind"]
    if kind in ("ok", "error"):
        if set(outcome) != {"kind"}:
            raise ValueError("malformed outcome")
        return "success" if kind == "ok" else "failure"
    if kind == "status":
        if set(outcome) != {"kind", "status"}:
            raise ValueError("malformed outcome")
        status = outcome["status"]
        if not is_status(status):
            raise ValueError("malformed status")
        return "failure" if status in failure_statuses else "neutral"
    raise ValueError("unknown outcome kind")
