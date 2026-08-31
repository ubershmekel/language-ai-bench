"""Evaluation of parsed programs under signed 64-bit two's complement rules."""

import os
from typing import Dict, cast

from parse import Node, Program, ProgramError

MASK = (1 << 64) - 1
SIGN = 1 << 63


def wrap(value: int) -> int:
    value &= MASK
    return value - (1 << 64) if value >= SIGN else value


def divide(left: int, right: int, at: int) -> int:
    if right == 0:
        raise ProgramError("DIVIDE_BY_ZERO", at)
    if os.environ.get("LAB_SABOTAGE") == "truncate-toward-negative":
        return wrap(left // right)
    quotient = abs(left) // abs(right)
    if (left < 0) != (right < 0):
        quotient = -quotient
    return wrap(quotient)


def remainder(left: int, right: int, at: int) -> int:
    if right == 0:
        raise ProgramError("DIVIDE_BY_ZERO", at)
    if os.environ.get("LAB_SABOTAGE") == "truncate-toward-negative":
        return wrap(left - (left // right) * right)
    quotient = abs(left) // abs(right)
    if (left < 0) != (right < 0):
        quotient = -quotient
    return wrap(left - quotient * right)


def shift(operator: str, left: int, right: int, at: int) -> int:
    if right < 0 or right > 63:
        if os.environ.get("LAB_SABOTAGE") != "shift-count-unchecked":
            raise ProgramError("SHIFT_RANGE", at)
        right &= 63
    if operator == "<<":
        return wrap(left << right)
    return wrap(left >> right)


def apply(operator: str, left: int, right: int, at: int) -> int:
    if operator == "+":
        return wrap(left + right)
    if operator == "-":
        return wrap(left - right)
    if operator == "*":
        return wrap(left * right)
    if operator == "/":
        return divide(left, right, at)
    if operator == "%":
        return remainder(left, right, at)
    if operator in ("<<", ">>"):
        return shift(operator, left, right, at)
    if operator == "&":
        return wrap(left & right)
    if operator == "|":
        return wrap(left | right)
    if operator == "^":
        return wrap(left ^ right)
    if operator == "==":
        return 1 if left == right else 0
    if operator == "!=":
        return 1 if left != right else 0
    if operator == "<":
        return 1 if left < right else 0
    if operator == "<=":
        return 1 if left <= right else 0
    if operator == ">":
        return 1 if left > right else 0
    return 1 if left >= right else 0


def evaluate_node(node: Node, scope: Dict[str, int]) -> int:
    kind = cast(str, node[0])
    if kind == "literal":
        return wrap(cast(int, node[1]))
    if kind == "name":
        name = cast(str, node[1])
        if name not in scope:
            raise ProgramError("UNDEFINED", cast(int, node[2]))
        return scope[name]
    if kind == "unary":
        value = evaluate_node(cast(Node, node[2]), scope)
        return wrap(-value) if node[1] == "-" else wrap(~value)
    left = evaluate_node(cast(Node, node[2]), scope)
    right = evaluate_node(cast(Node, node[3]), scope)
    return apply(cast(str, node[1]), left, right, cast(int, node[4]))


def evaluate(program: Program) -> int:
    scope: Dict[str, int] = {}
    for name, node in program.bindings:
        scope[name] = evaluate_node(node, scope)
    return evaluate_node(program.body, scope)
