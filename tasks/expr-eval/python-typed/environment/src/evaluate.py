"""Evaluation of the tokens the current parser produces."""

from typing import List, cast

from parse import Token


def evaluate(tokens: List[Token]) -> int:
    """Left to right, with no precedence between the operators."""
    value = cast(int, tokens[0][0])
    index = 1
    while index < len(tokens):
        operator = cast(str, tokens[index][0])
        right = cast(int, tokens[index + 1][0])
        value = value + right if operator == "+" else value * right
        index += 2
    return value
