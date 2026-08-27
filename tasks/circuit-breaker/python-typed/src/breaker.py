"""Circuit-breaker state transitions."""

from typing import TypedDict

from parse import Config, Outcome, State


class Breaker(TypedDict):
    state: State
    failures: int
    openedAt: int
    probes: int


def new_breaker() -> Breaker:
    return {"state": "closed", "failures": 0, "openedAt": 0, "probes": 0}


def observe(breaker: Breaker, at: int, config: Config) -> State:
    """The state the breaker is in when a call arrives."""
    return breaker["state"]


def admit(breaker: Breaker, observed: State, config: Config) -> bool:
    return observed != "open"


def record(
    breaker: Breaker, observed: State, outcome: Outcome, at: int, config: Config
) -> None:
    if outcome == "success":
        breaker["failures"] = 0
        return
    breaker["failures"] += 1
    if breaker["failures"] >= config["threshold"]:
        breaker["state"] = "open"
        breaker["openedAt"] = at
