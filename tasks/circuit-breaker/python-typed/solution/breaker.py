"""Circuit-breaker state transitions."""

import os
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
    """Advance an expired open breaker, then report the state the call sees."""
    if breaker["state"] == "open":
        elapsed = at - breaker["openedAt"]
        if os.environ.get("LAB_SABOTAGE") == "cooldown-off-by-one":
            ready = elapsed > config["cooldownMs"]
        else:
            ready = elapsed >= config["cooldownMs"]
        if ready:
            breaker["state"] = "half-open"
            breaker["probes"] = 0
    return breaker["state"]


def admit(breaker: Breaker, observed: State, config: Config) -> bool:
    if observed == "open":
        return False
    if observed != "half-open":
        return True
    if os.environ.get("LAB_SABOTAGE") == "no-half-open-limit":
        return True
    return breaker["probes"] < config["halfOpenLimit"]


def record(
    breaker: Breaker, observed: State, outcome: Outcome, at: int, config: Config
) -> None:
    if observed == "half-open":
        breaker["probes"] += 1
    effective: Outcome = outcome
    if os.environ.get("LAB_SABOTAGE") == "neutral-counts-as-success":
        effective = "success" if outcome == "neutral" else outcome
    if effective == "neutral":
        return
    if effective == "success":
        breaker["failures"] = 0
        if observed == "half-open":
            breaker["state"] = "closed"
        return
    breaker["failures"] += 1
    if observed == "half-open" or breaker["failures"] >= config["threshold"]:
        breaker["state"] = "open"
        breaker["openedAt"] = at
