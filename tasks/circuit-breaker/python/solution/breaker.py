"""Circuit-breaker state transitions."""

import os


def new_breaker():
    return {"state": "closed", "failures": 0, "openedAt": 0, "probes": 0}


def observe(breaker, at, config):
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


def admit(breaker, observed, config):
    if observed == "open":
        return False
    if observed != "half-open":
        return True
    if os.environ.get("LAB_SABOTAGE") == "no-half-open-limit":
        return True
    return breaker["probes"] < config["halfOpenLimit"]


def record(breaker, observed, outcome, at, config):
    if observed == "half-open":
        breaker["probes"] += 1
    if os.environ.get("LAB_SABOTAGE") == "neutral-counts-as-success":
        outcome = "success" if outcome == "neutral" else outcome
    if outcome == "neutral":
        return
    if outcome == "success":
        breaker["failures"] = 0
        if observed == "half-open":
            breaker["state"] = "closed"
        return
    breaker["failures"] += 1
    if observed == "half-open":
        breaker["state"] = "open"
        breaker["openedAt"] = at
    elif breaker["failures"] >= config["threshold"]:
        breaker["state"] = "open"
        breaker["openedAt"] = at
