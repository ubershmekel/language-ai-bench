"""Evaluation of parsed programs under signed 64-bit two's complement rules."""

import os

from parse import ProgramError

MASK = (1 << 64) - 1
SIGN = 1 << 63


def wrap(value):
    value &= MASK
    return value - (1 << 64) if value >= SIGN else value


def divide(left, right, at):
    if right == 0:
        raise_error("DIVIDE_BY_ZERO", at)
    if os.environ.get("LAB_SABOTAGE") == "truncate-toward-negative":
        return wrap(left // right)
    quotient = abs(left) // abs(right)
    if (left < 0) != (right < 0):
        quotient = -quotient
    return wrap(quotient)


def remainder(left, right, at):
    if right == 0:
        raise_error("DIVIDE_BY_ZERO", at)
    if os.environ.get("LAB_SABOTAGE") == "truncate-toward-negative":
        return wrap(left - (left // right) * right)
    quotient = abs(left) // abs(right)
    if (left < 0) != (right < 0):
        quotient = -quotient
    return wrap(left - quotient * right)


def shift(operator, left, right, at):
    if right < 0 or right > 63:
        if os.environ.get("LAB_SABOTAGE") != "shift-count-unchecked":
            raise_error("SHIFT_RANGE", at)
        right &= 63
    if operator == "<<":
        return wrap(left << right)
    return wrap(left >> right)


def raise_error(code, at):
    raise ProgramError(code, at)


def apply(operator, left, right, at):
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


def evaluate_node(node, scope):
    kind = node[0]
    if kind == "literal":
        return wrap(node[1])
    if kind == "name":
        if node[1] not in scope:
            raise_error("UNDEFINED", node[2])
        return scope[node[1]]
    if kind == "unary":
        value = evaluate_node(node[2], scope)
        return wrap(-value) if node[1] == "-" else wrap(~value)
    left = evaluate_node(node[2], scope)
    right = evaluate_node(node[3], scope)
    return apply(node[1], left, right, node[4])


def evaluate(program):
    scope = {}
    for name, node in program["bindings"]:
        scope[name] = evaluate_node(node, scope)
    return evaluate_node(program["body"], scope)
