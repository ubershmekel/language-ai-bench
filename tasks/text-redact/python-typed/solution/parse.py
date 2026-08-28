"""Validate the redaction request and its rules."""

import re
from typing import Literal, TypedDict, Union

Policy = Literal["merge", "strict"]


class LiteralRule(TypedDict):
    id: str
    kind: Literal["literal"]
    value: str


class SpanRule(TypedDict):
    id: str
    kind: Literal["span"]
    start: int
    end: int


Rule = Union[LiteralRule, SpanRule]


class Config(TypedDict):
    mask: str
    policy: Policy
    minLength: int


class Document(TypedDict):
    config: object
    text: str
    rules: list[object]


class Span(TypedDict):
    start: int
    end: int
    rules: list[str]


TOP_LEVEL = {"config", "text", "rules"}
CONFIG_KEYS = {"mask", "policy", "minLength"}
LITERAL_KEYS = {"id", "kind", "value"}
SPAN_KEYS = {"id", "kind", "start", "end"}
POLICIES = ("merge", "strict")
RULE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


def is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def code_points(text: str) -> list[str]:
    """The text as a list of Unicode code points."""
    return list(text)


def parse_document(value: object) -> Document:
    if not isinstance(value, dict) or set(value) != TOP_LEVEL:
        raise ValueError("malformed document")
    text = value["text"]
    rules = value["rules"]
    if not isinstance(text, str):
        raise ValueError("malformed text")
    if not isinstance(rules, list):
        raise ValueError("malformed rules")
    return {"config": value["config"], "text": text, "rules": rules}


def parse_config(value: object) -> Config:
    if not isinstance(value, dict) or set(value) != CONFIG_KEYS:
        raise ValueError("malformed config")
    mask = value["mask"]
    policy = value["policy"]
    minimum = value["minLength"]
    if not isinstance(mask, str) or len(code_points(mask)) != 1:
        raise ValueError("malformed mask")
    if not isinstance(policy, str) or policy not in POLICIES:
        raise ValueError("malformed policy")
    if not is_int(minimum) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("malformed minimum length")
    checked: Policy = "strict" if policy == "strict" else "merge"
    return {"mask": mask, "policy": checked, "minLength": minimum}


def parse_rule(value: object, seen: set[str], length: int) -> Rule:
    if not isinstance(value, dict) or "kind" not in value:
        raise ValueError("malformed rule")
    identifier = value.get("id")
    if not isinstance(identifier, str) or not RULE_ID.match(identifier):
        raise ValueError("malformed rule id")
    if identifier in seen:
        raise ValueError("duplicate rule id")
    kind = value["kind"]
    if kind == "literal":
        if set(value) != LITERAL_KEYS:
            raise ValueError("malformed literal rule")
        text = value["value"]
        if not isinstance(text, str) or not text:
            raise ValueError("malformed literal value")
        return {"id": identifier, "kind": "literal", "value": text}
    if kind == "span":
        if set(value) != SPAN_KEYS:
            raise ValueError("malformed span rule")
        start = value["start"]
        end = value["end"]
        if not is_int(start) or not is_int(end):
            raise ValueError("malformed span bounds")
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("malformed span bounds")
        if start < 0 or start >= end or end > length:
            raise ValueError("malformed span bounds")
        return {"id": identifier, "kind": "span", "start": start, "end": end}
    raise ValueError("unknown rule kind")
