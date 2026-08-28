"""Find the regions a rule matches and mask them."""

from parse import LiteralRule, Span

Found = tuple[int, int]
Attributed = tuple[int, int, str]


def find_spans(rule: LiteralRule, text: str) -> list[Found]:
    """Scan for the literal one position at a time."""
    spans: list[Found] = []
    width = len(rule["value"])
    index = 0
    while index + width <= len(text):
        if text[index : index + width] == rule["value"]:
            spans.append((index, index + width))
        index += 1
    return spans


def merge_spans(spans: list[Attributed]) -> list[Span]:
    """Spans are reported in the order they were found."""
    return [
        {"start": start, "end": end, "rules": [identifier]}
        for start, end, identifier in spans
    ]


def apply_mask(text: str, spans: list[Span], mask: str) -> str:
    characters = list(text)
    for span in spans:
        for index in range(span["start"], span["end"]):
            characters[index] = mask
    return "".join(characters)
