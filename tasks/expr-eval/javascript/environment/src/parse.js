"use strict";

const TOP_LEVEL = ["config", "programs"];

/** Only the top-level key set is checked so far. */
function parseDocument(value) {
  if (Object.keys(value).sort().join(",") !== TOP_LEVEL.join(",")) {
    throw new Error("malformed document");
  }
  return { maxDepth: value.config.maxDepth, programs: value.programs };
}

/** Decimal literals and the two operators that are understood so far. */
function tokenize(source) {
  const tokens = [];
  let index = 0;
  while (index < source.length) {
    const character = source[index];
    if (character === " ") {
      index += 1;
      continue;
    }
    if (character === "+" || character === "*") {
      tokens.push({ value: character, at: index });
      index += 1;
      continue;
    }
    const start = index;
    while (index < source.length && source[index] >= "0" && source[index] <= "9") {
      index += 1;
    }
    if (index === start) {
      throw new Error(`unexpected character at ${index}`);
    }
    tokens.push({ value: Number(source.slice(start, index)), at: start });
  }
  return tokens;
}

module.exports = { parseDocument, tokenize };
