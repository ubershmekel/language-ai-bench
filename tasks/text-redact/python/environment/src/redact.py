"""Find the regions a rule matches and mask them."""


def find_spans(rule, text):
    """Scan for the literal one position at a time."""
    spans = []
    width = len(rule["value"])
    index = 0
    while index + width <= len(text):
        if text[index : index + width] == rule["value"]:
            spans.append((index, index + width))
        index += 1
    return spans


def merge_spans(spans):
    """Spans are reported in the order they were found."""
    return [
        {"start": start, "end": end, "rules": [identifier]}
        for start, end, identifier in spans
    ]


def apply_mask(text, spans, mask):
    characters = list(text)
    for span in spans:
        for index in range(span["start"], span["end"]):
            characters[index] = mask
    return "".join(characters)
