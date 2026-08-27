import json
import sys
from typing import TypedDict, cast

from fx import Rate, build_graph, factor
from money import format_minor, parse_amount, round_amount
from rollup import Item, rollup

TOP_LEVEL = {"reportCurrency", "currencies", "rates", "entries"}


class Entry(TypedDict):
    account: str
    currency: str
    amount: str


class Ledger(TypedDict):
    reportCurrency: str
    currencies: dict[str, int]
    rates: list[Rate]
    entries: list[Entry]


class Account(TypedDict):
    account: str
    total: str


class Report(TypedDict):
    reportCurrency: str
    accounts: list[Account]


def as_ledger(value: object) -> Ledger:
    """Accept the parsed input as a ledger.

    The current implementation checks only the top-level key set and trusts
    every value below it.
    """
    if not isinstance(value, dict) or set(value) != TOP_LEVEL:
        raise ValueError("malformed document")
    return cast(Ledger, value)


def build_report(ledger: Ledger) -> Report:
    currencies = ledger["currencies"]
    report = ledger["reportCurrency"]
    if report not in currencies:
        raise ValueError("unknown report currency")
    edges = build_graph(currencies, ledger["rates"])
    places = currencies[report]
    items: list[Item] = []
    for entry in ledger["entries"]:
        code = entry["currency"]
        amount = parse_amount(entry["amount"], currencies[code])
        converted = amount * factor(edges, code, report)
        items.append((entry["account"], round_amount(converted, places)))
    return {
        "reportCurrency": report,
        "accounts": [
            {"account": account, "total": format_minor(total, places)}
            for account, total in rollup(items)
        ],
    }


try:
    print(
        json.dumps(
            build_report(as_ledger(json.load(sys.stdin))), separators=(",", ":")
        )
    )
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
