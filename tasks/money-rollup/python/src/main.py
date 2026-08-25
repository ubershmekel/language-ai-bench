import json
import sys

from fx import build_graph, factor
from money import format_minor, parse_amount, round_amount
from rollup import rollup

TOP_LEVEL = {"reportCurrency", "currencies", "rates", "entries"}


def build_report(document):
    if not isinstance(document, dict) or set(document) != TOP_LEVEL:
        raise ValueError("malformed document")
    currencies = document["currencies"]
    report = document["reportCurrency"]
    if report not in currencies:
        raise ValueError("unknown report currency")
    edges = build_graph(currencies, document["rates"])
    places = currencies[report]
    items = []
    for entry in document["entries"]:
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
    print(json.dumps(build_report(json.load(sys.stdin)), separators=(",", ":")))
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
