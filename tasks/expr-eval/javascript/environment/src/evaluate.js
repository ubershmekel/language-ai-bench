"use strict";

/** Left to right, with no precedence between the operators. */
function evaluate(tokens) {
  let value = tokens[0].value;
  let index = 1;
  while (index < tokens.length) {
    const operator = tokens[index].value;
    const right = tokens[index + 1].value;
    value = operator === "+" ? value + right : value * right;
    index += 2;
  }
  return value;
}

module.exports = { evaluate };
