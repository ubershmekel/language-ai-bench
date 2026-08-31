"use strict";

const { ProgramError } = require("./parse");

const WIDTH = 64n;

function wrap(value) {
  return BigInt.asIntN(64, value);
}

function divide(left, right, at) {
  if (right === 0n) {
    throw new ProgramError("DIVIDE_BY_ZERO", at);
  }
  if (process.env.LAB_SABOTAGE === "truncate-toward-negative") {
    let quotient = left / right;
    if (left % right !== 0n && (left < 0n) !== (right < 0n)) {
      quotient -= 1n;
    }
    return wrap(quotient);
  }
  return wrap(left / right);
}

function remainder(left, right, at) {
  if (right === 0n) {
    throw new ProgramError("DIVIDE_BY_ZERO", at);
  }
  if (process.env.LAB_SABOTAGE === "truncate-toward-negative") {
    let quotient = left / right;
    if (left % right !== 0n && (left < 0n) !== (right < 0n)) {
      quotient -= 1n;
    }
    return wrap(left - quotient * right);
  }
  return wrap(left % right);
}

function shift(operator, left, right, at) {
  let count = right;
  if (count < 0n || count > 63n) {
    if (process.env.LAB_SABOTAGE !== "shift-count-unchecked") {
      throw new ProgramError("SHIFT_RANGE", at);
    }
    count &= 63n;
  }
  return wrap(operator === "<<" ? left << count : left >> count);
}

function applyOperator(operator, left, right, at) {
  switch (operator) {
    case "+":
      return wrap(left + right);
    case "-":
      return wrap(left - right);
    case "*":
      return wrap(left * right);
    case "/":
      return divide(left, right, at);
    case "%":
      return remainder(left, right, at);
    case "<<":
    case ">>":
      return shift(operator, left, right, at);
    case "&":
      return wrap(left & right);
    case "|":
      return wrap(left | right);
    case "^":
      return wrap(left ^ right);
    case "==":
      return left === right ? 1n : 0n;
    case "!=":
      return left !== right ? 1n : 0n;
    case "<":
      return left < right ? 1n : 0n;
    case "<=":
      return left <= right ? 1n : 0n;
    case ">":
      return left > right ? 1n : 0n;
    default:
      return left >= right ? 1n : 0n;
  }
}

function evaluateNode(node, scope) {
  if (node.kind === "literal") {
    return wrap(node.value);
  }
  if (node.kind === "name") {
    if (!scope.has(node.name)) {
      throw new ProgramError("UNDEFINED", node.at);
    }
    return scope.get(node.name);
  }
  if (node.kind === "unary") {
    const value = evaluateNode(node.operand, scope);
    return wrap(node.operator === "-" ? -value : ~value);
  }
  const left = evaluateNode(node.left, scope);
  const right = evaluateNode(node.right, scope);
  return applyOperator(node.operator, left, right, node.at);
}

function evaluate(program) {
  const scope = new Map();
  for (const binding of program.bindings) {
    scope.set(binding.name, evaluateNode(binding.node, scope));
  }
  return evaluateNode(program.body, scope);
}

module.exports = { evaluate, wrap, WIDTH };
