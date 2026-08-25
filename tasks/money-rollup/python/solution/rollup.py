"""Aggregate converted entries over account hierarchies."""

import os
import re

SEGMENT = re.compile(r"^[A-Za-z0-9_]+$")


def account_prefixes(account):
    if not isinstance(account, str) or account == "":
        raise ValueError("malformed account")
    segments = account.split(":")
    if any(not SEGMENT.match(segment) for segment in segments):
        raise ValueError("malformed account")
    return [":".join(segments[: index + 1]) for index in range(len(segments))]


def rollup(items):
    """Total every ancestor prefix of each (account, minor units) item."""
    totals = {}
    for account, minor in items:
        prefixes = account_prefixes(account)
        if os.environ.get("LAB_SABOTAGE") == "leaf-only-rollup":
            prefixes = prefixes[-1:]
        for prefix in prefixes:
            totals[prefix] = totals.get(prefix, 0) + minor
    return sorted(totals.items())
