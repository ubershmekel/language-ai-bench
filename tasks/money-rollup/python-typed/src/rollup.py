"""Aggregate converted entries by account."""

Item = tuple[str, int]


def rollup(items: list[Item]) -> list[Item]:
    """Total each account named by an entry."""
    totals: dict[str, int] = {}
    for account, minor in items:
        totals[account] = totals.get(account, 0) + minor
    return sorted(totals.items())
