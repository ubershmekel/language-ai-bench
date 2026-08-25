import json
import sys

from fx import build_graph, factor
from money import format_minor, parse_amount, round_half_even
from rollup import rollup

TOP_LEVEL = {"reportCurrency", "currencies", "rates", "entries"}
ENTRY = {"account", "currency", "amount"}


def build_report(document):
    if not isinstance(document, dict) or set(document) != TOP_LEVEL:
        raise ValueError("malformed document")
    currencies = document["currencies"]
    if not isinstance(currencies, dict) or not currencies:
        raise ValueError("malformed currencies")
    for minor_units in currencies.values():
        if not isinstance(minor_units, int) or isinstance(minor_units, bool):
            raise ValueError("malformed minor units")
        if not 0 <= minor_units <= 4:
            raise ValueError("malformed minor units")
    report = document["reportCurrency"]
    if not isinstance(report, str) or report not in currencies:
        raise ValueError("unknown report currency")
    if not isinstance(document["rates"], list):
        raise ValueError("malformed rates")
    if not isinstance(document["entries"], list):
        raise ValueError("malformed entries")
    edges = build_graph(currencies, document["rates"])
    places = currencies[report]
    items = []
    for entry in document["entries"]:
        if not isinstance(entry, dict) or set(entry) != ENTRY:
            raise ValueError("malformed entry")
        code = entry["currency"]
        if not isinstance(code, str) or code not in currencies:
            raise ValueError("unknown entry currency")
        amount = parse_amount(entry["amount"], currencies[code])
        converted = amount * factor(edges, code, report)
        items.append((entry["account"], round_half_even(converted, places)))
    return {
        "reportCurrency": report,
        "accounts": [
            {"account": account, "total": format_minor(total, places)}
            for account, total in rollup(items)
        ],
    }


try:
    print(json.dumps(build_report(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
