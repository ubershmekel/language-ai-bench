"""Currency rate lookup."""

from money import parse_rate


def build_graph(currencies, rates):
    edges = {}
    for rate in rates:
        edges[(rate["from"], rate["to"])] = parse_rate(rate["rate"])
    return edges


def factor(edges, source, target):
    if source == target:
        return 1.0
    if (source, target) not in edges:
        raise ValueError("no conversion rate")
    return edges[(source, target)]
