"""Read the redaction configuration and the rules."""

from typing import Literal, TypedDict, Union, cast

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
    config: Config
    text: str
    rules: list[Rule]


class Span(TypedDict):
    start: int
    end: int
    rules: list[str]


TOP_LEVEL = {"config", "text", "rules"}


def parse_document(value: object) -> Document:
    """Accept the parsed input as a redaction request.

    The current implementation checks only the top-level key set and trusts
    every value below it.
    """
    if not isinstance(value, dict) or set(value) != TOP_LEVEL:
        raise ValueError("malformed document")
    return cast(Document, value)


def parse_config(value: Config) -> Config:
    return {
        "mask": value["mask"],
        "policy": value["policy"],
        "minLength": value["minLength"],
    }


def parse_rule(value: Rule, seen: set[str], length: int) -> LiteralRule:
    """Only literal rules are understood so far."""
    if value["kind"] != "literal":
        raise ValueError("unsupported rule kind")
    return {"id": value["id"], "kind": "literal", "value": value["value"]}
