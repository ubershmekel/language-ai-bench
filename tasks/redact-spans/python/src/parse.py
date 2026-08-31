"""Read the redaction configuration and the rules."""

TOP_LEVEL = {"config", "text", "rules"}


def parse_document(value):
    """Accept the parsed input as a redaction request.

    The current implementation checks only the top-level key set and trusts
    every value below it.
    """
    if not isinstance(value, dict) or set(value) != TOP_LEVEL:
        raise ValueError("malformed document")
    return value


def parse_config(value):
    return {
        "mask": value["mask"],
        "policy": value["policy"],
        "minLength": value["minLength"],
    }


def parse_rule(value, seen, length):
    """Only literal rules are understood so far."""
    if value["kind"] != "literal":
        raise ValueError("unsupported rule kind")
    return {"id": value["id"], "kind": "literal", "value": value["value"]}
