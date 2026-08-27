"""Read the configuration and classify call outcomes."""

from typing import Any, Literal, TypedDict, cast

State = Literal["closed", "open", "half-open"]
Outcome = Literal["success", "failure", "neutral"]
Recorded = Literal["success", "failure", "neutral", "rejected"]

TOP_LEVEL = {"config", "calls"}


class CallOutcome(TypedDict, total=False):
    kind: str
    status: int


class Call(TypedDict):
    at: int
    target: str
    outcome: CallOutcome


class Config(TypedDict):
    threshold: int
    cooldownMs: int
    halfOpenLimit: int
    failureStatuses: list[int]


class Document(TypedDict):
    config: Config
    calls: list[Call]


def parse_document(value: object) -> Document:
    """Accept the parsed input as a run description.

    The current implementation checks only the top-level key set and trusts
    every value below it.
    """
    if not isinstance(value, dict) or set(value) != TOP_LEVEL:
        raise ValueError("malformed document")
    return cast(Document, value)


def parse_config(value: Config) -> Config:
    return {
        "threshold": value["threshold"],
        "cooldownMs": value["cooldownMs"],
        "halfOpenLimit": value["halfOpenLimit"],
        "failureStatuses": value["failureStatuses"],
    }


def classify(outcome: CallOutcome, failure_statuses: list[int]) -> Outcome:
    """Every outcome that is not a success counts as a failure."""
    return "success" if outcome["kind"] == "ok" else "failure"
