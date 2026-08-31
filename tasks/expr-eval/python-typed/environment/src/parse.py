"""Document handling and a first pass at reading program sources."""

from typing import Any, Dict, List, Tuple

TOP_LEVEL = ["config", "programs"]

Token = Tuple[Any, int]


def parse_document(value: Dict[str, Any]) -> Dict[str, Any]:
    """Only the top-level key set is checked so far."""
    if sorted(value.keys()) != TOP_LEVEL:
        raise ValueError("malformed document")
    return {
        "max_depth": value["config"]["maxDepth"],
        "programs": value["programs"],
    }


def tokenize(source: str) -> List[Token]:
    """Decimal literals and the two operators that are understood so far."""
    tokens: List[Token] = []
    index = 0
    while index < len(source):
        character = source[index]
        if character == " ":
            index += 1
            continue
        if character in "+*":
            tokens.append((character, index))
            index += 1
            continue
        start = index
        while index < len(source) and source[index].isdigit():
            index += 1
        if index == start:
            raise ValueError(f"unexpected character at {index}")
        tokens.append((int(source[start:index]), start))
    return tokens
