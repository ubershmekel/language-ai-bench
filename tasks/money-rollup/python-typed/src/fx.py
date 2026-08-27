"""Currency rate lookup."""

from typing import TypedDict

from money import parse_rate

Rate = TypedDict("Rate", {"from": str, "to": str, "rate": str})

Graph = dict[tuple[str, str], float]


def build_graph(currencies: dict[str, int], rates: list[Rate]) -> Graph:
    edges: Graph = {}
    for rate in rates:
        edges[(rate["from"], rate["to"])] = parse_rate(rate["rate"])
    return edges


def factor(edges: Graph, source: str, target: str) -> float:
    if source == target:
        return 1.0
    if (source, target) not in edges:
        raise ValueError("no conversion rate")
    return edges[(source, target)]
