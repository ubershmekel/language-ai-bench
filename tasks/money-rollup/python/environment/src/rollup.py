"""Aggregate converted entries by account."""


def rollup(items):
    """Total each account named by an entry."""
    totals = {}
    for account, minor in items:
        totals[account] = totals.get(account, 0) + minor
    return sorted(totals.items())
