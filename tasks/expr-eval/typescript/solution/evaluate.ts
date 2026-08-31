import { Node, Program, ProgramError } from "./parse";

function wrap(value: bigint): bigint {
  return BigInt.asIntN(64, value);
}

function flooredQuotient(left: bigint, right: bigint): bigint {
  let quotient = left / right;
  if (left % right !== 0n && left < 0n !== right < 0n) {
    quotient -= 1n;
  }
  return quotient;
}

function divide(left: bigint, right: bigint, at: number): bigint {
  if (right === 0n) {
    throw new ProgramError("DIVIDE_BY_ZERO", at);
  }
  if (process.env["LAB_SABOTAGE"] === "truncate-toward-negative") {
    return wrap(flooredQuotient(left, right));
  }
  return wrap(left / right);
}

function remainder(left: bigint, right: bigint, at: number): bigint {
  if (right === 0n) {
    throw new ProgramError("DIVIDE_BY_ZERO", at);
  }
  if (process.env["LAB_SABOTAGE"] === "truncate-toward-negative") {
    return wrap(left - flooredQuotient(left, right) * right);
  }
  return wrap(left % right);
}

function shift(operator: string, left: bigint, right: bigint, at: number): bigint {
  let count = right;
  if (count < 0n || count > 63n) {
    if (process.env["LAB_SABOTAGE"] !== "shift-count-unchecked") {
      throw new ProgramError("SHIFT_RANGE", at);
    }
    count &= 63n;
  }
  return wrap(operator === "<<" ? left << count : left >> count);
}

function applyOperator(operator: string, left: bigint, right: bigint, at: number): bigint {
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

function evaluateNode(node: Node, scope: Map<string, bigint>): bigint {
  if (node.kind === "literal") {
    return wrap(node.value);
  }
  if (node.kind === "name") {
    const value = scope.get(node.name);
    if (value === undefined) {
      throw new ProgramError("UNDEFINED", node.at);
    }
    return value;
  }
  if (node.kind === "unary") {
    const value = evaluateNode(node.operand, scope);
    return wrap(node.operator === "-" ? -value : ~value);
  }
  const left = evaluateNode(node.left, scope);
  const right = evaluateNode(node.right, scope);
  return applyOperator(node.operator, left, right, node.at);
}

export function evaluate(program: Program): bigint {
  const scope = new Map<string, bigint>();
  for (const binding of program.bindings) {
    scope.set(binding.name, evaluateNode(binding.node, scope));
  }
  return evaluateNode(program.body, scope);
}
