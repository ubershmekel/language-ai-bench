"""Evaluation of the tokens the current parser produces."""


def evaluate(tokens):
    """Left to right, with no precedence between the operators."""
    value = tokens[0][0]
    index = 1
    while index < len(tokens):
        operator = tokens[index][0]
        right = tokens[index + 1][0]
        value = value + right if operator == "+" else value * right
        index += 2
    return value
