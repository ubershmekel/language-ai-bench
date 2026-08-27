"""Read the configuration and classify call outcomes."""

TOP_LEVEL = {"config", "calls"}


def parse_document(value):
    """Accept the parsed input as a run description.

    The current implementation checks only the top-level key set and trusts
    every value below it.
    """
    if not isinstance(value, dict) or set(value) != TOP_LEVEL:
        raise ValueError("malformed document")
    return value


def parse_config(value):
    return {
        "threshold": value["threshold"],
        "cooldownMs": value["cooldownMs"],
        "halfOpenLimit": value["halfOpenLimit"],
        "failureStatuses": value["failureStatuses"],
    }


def classify(outcome, failure_statuses):
    """Every outcome that is not a success counts as a failure."""
    return "success" if outcome["kind"] == "ok" else "failure"
