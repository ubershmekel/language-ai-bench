"""Circuit-breaker state transitions."""


def new_breaker():
    return {"state": "closed", "failures": 0, "openedAt": 0, "probes": 0}


def observe(breaker, at, config):
    """The state the breaker is in when a call arrives."""
    return breaker["state"]


def admit(breaker, observed, config):
    return observed != "open"


def record(breaker, observed, outcome, at, config):
    if outcome == "success":
        breaker["failures"] = 0
        return
    breaker["failures"] += 1
    if breaker["failures"] >= config["threshold"]:
        breaker["state"] = "open"
        breaker["openedAt"] = at
