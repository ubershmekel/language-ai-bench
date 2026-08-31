import { Token } from "./parse";

/** Left to right, with no precedence between the operators. */
export function evaluate(tokens: Token[]): number {
  let value = (tokens[0] as Token).value as number;
  let index = 1;
  while (index < tokens.length) {
    const operator = (tokens[index] as Token).value as string;
    const right = (tokens[index + 1] as Token).value as number;
    value = operator === "+" ? value + right : value * right;
    index += 2;
  }
  return value;
}
