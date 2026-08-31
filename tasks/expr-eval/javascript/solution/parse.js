"use strict";

const TOP_LEVEL = ["config", "programs"];
const CONFIG_KEYS = ["maxDepth"];
const PROGRAM_KEYS = ["id", "source"];
const PROGRAM_ID = /^[A-Za-z0-9_.-]+$/;
const IDENT_START = /[A-Za-z_]/;
const IDENT_PART = /[A-Za-z0-9_]/;
const DIGIT = /[0-9]/;
const HEX = /[0-9a-fA-F]/;
const UNSIGNED_LIMIT = (1n << 64n) - 1n;

const OPERATORS = [
  "<<", ">>", "==", "!=", "<=", ">=",
  "(", ")", ";", "=", "+", "-", "*", "/", "%", "&", "|", "^", "~", "<", ">",
];

const BINARY_LEVELS = [
  ["|"],
  ["^"],
  ["&"],
  ["==", "!="],
  ["<", "<=", ">", ">="],
  ["<<", ">>"],
  ["+", "-"],
  ["*", "/", "%"],
];

/** A fault in one program's source, reported instead of a value. */
class ProgramError extends Error {
  constructor(code, at) {
    super(code);
    this.code = code;
    this.at = at;
  }
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasKeys(value, keys) {
  return Object.keys(value).sort().join(",") === keys.join(",");
}

function isInteger(value) {
  return typeof value === "number" && Number.isInteger(value);
}

function parseDocument(value) {
  if (!isObject(value) || !hasKeys(value, TOP_LEVEL)) {
    throw new Error("malformed document");
  }
  const config = value.config;
  if (!isObject(config) || !hasKeys(config, CONFIG_KEYS)) {
    throw new Error("malformed config");
  }
  if (!isInteger(config.maxDepth) || config.maxDepth < 1) {
    throw new Error("malformed maxDepth");
  }
  if (!Array.isArray(value.programs)) {
    throw new Error("malformed programs");
  }
  const seen = new Set();
  const programs = [];
  for (const item of value.programs) {
    if (!isObject(item) || !hasKeys(item, PROGRAM_KEYS)) {
      throw new Error("malformed program");
    }
    if (typeof item.id !== "string" || !PROGRAM_ID.test(item.id)) {
      throw new Error("malformed id");
    }
    if (seen.has(item.id)) {
      throw new Error("duplicate id");
    }
    if (typeof item.source !== "string") {
      throw new Error("malformed source");
    }
    seen.add(item.id);
    programs.push({ id: item.id, source: item.source });
  }
  return { maxDepth: config.maxDepth, programs };
}

/** Source as a list of tokens, with offsets counted in code points. */
function tokenize(source) {
  const points = Array.from(source);
  const tokens = [];
  let index = 0;
  while (index < points.length) {
    const character = points[index];
    if (character === " " || character === "\t" || character === "\r" || character === "\n") {
      index += 1;
      continue;
    }
    if (DIGIT.test(character)) {
      const start = index;
      let value;
      if (
        character === "0" &&
        index + 1 < points.length &&
        (points[index + 1] === "x" || points[index + 1] === "X")
      ) {
        index += 2;
        const digits = index;
        while (index < points.length && HEX.test(points[index])) {
          index += 1;
        }
        if (index === digits) {
          throw new ProgramError("PARSE", start);
        }
        value = BigInt(`0x${points.slice(digits, index).join("")}`);
      } else {
        while (index < points.length && DIGIT.test(points[index])) {
          index += 1;
        }
        value = BigInt(points.slice(start, index).join(""));
      }
      if (index < points.length && IDENT_PART.test(points[index])) {
        throw new ProgramError("PARSE", index);
      }
      if (value > UNSIGNED_LIMIT) {
        if (process.env.LAB_SABOTAGE !== "literal-range-unchecked") {
          throw new ProgramError("LITERAL_RANGE", start);
        }
        value &= UNSIGNED_LIMIT;
      }
      tokens.push({ kind: "int", value, at: start });
      continue;
    }
    if (IDENT_START.test(character)) {
      const start = index;
      while (index < points.length && IDENT_PART.test(points[index])) {
        index += 1;
      }
      const text = points.slice(start, index).join("");
      tokens.push({ kind: text === "let" ? "let" : "ident", text, at: start });
      continue;
    }
    const operator = OPERATORS.find(
      (candidate) => points.slice(index, index + candidate.length).join("") === candidate,
    );
    if (!operator) {
      throw new ProgramError("PARSE", index);
    }
    tokens.push({ kind: operator, text: operator, at: index });
    index += operator.length;
  }
  tokens.push({ kind: "end", text: "", at: points.length });
  return tokens;
}

class Parser {
  constructor(tokens, maxDepth) {
    this.tokens = tokens;
    this.maxDepth = maxDepth;
    this.index = 0;
    this.depth = 0;
    this.levels = BINARY_LEVELS.map((level) => level);
    if (process.env.LAB_SABOTAGE === "precedence-additive-first") {
      const last = this.levels.length - 1;
      const swap = this.levels[last];
      this.levels[last] = this.levels[last - 1];
      this.levels[last - 1] = swap;
    }
  }

  peek() {
    return this.tokens[this.index];
  }

  take() {
    return this.tokens[this.index++];
  }

  expect(kind) {
    const token = this.peek();
    if (token.kind !== kind) {
      throw new ProgramError("PARSE", token.at);
    }
    return this.take();
  }

  parseProgram() {
    const bindings = [];
    while (this.peek().kind === "let") {
      this.take();
      const name = this.expect("ident");
      this.expect("=");
      bindings.push({ name: name.text, node: this.parseExpression(0) });
      this.expect(";");
    }
    const body = this.parseExpression(0);
    if (this.peek().kind !== "end") {
      throw new ProgramError("PARSE", this.peek().at);
    }
    return { bindings, body };
  }

  parseExpression(level) {
    if (level >= this.levels.length) {
      return this.parseUnary();
    }
    let node = this.parseExpression(level + 1);
    while (this.levels[level].includes(this.peek().kind)) {
      const operator = this.take();
      const right = this.parseExpression(level + 1);
      node = { kind: "binary", operator: operator.kind, left: node, right, at: operator.at };
    }
    return node;
  }

  parseUnary() {
    const token = this.peek();
    if (token.kind === "-" || token.kind === "~") {
      this.take();
      return { kind: "unary", operator: token.kind, operand: this.parseUnary(), at: token.at };
    }
    return this.parsePrimary();
  }

  parsePrimary() {
    const token = this.peek();
    if (token.kind === "int") {
      this.take();
      return { kind: "literal", value: token.value, at: token.at };
    }
    if (token.kind === "ident") {
      this.take();
      return { kind: "name", name: token.text, at: token.at };
    }
    if (token.kind === "(") {
      this.depth += 1;
      if (this.depth > this.maxDepth) {
        throw new ProgramError("DEPTH", token.at);
      }
      this.take();
      const node = this.parseExpression(0);
      this.expect(")");
      this.depth -= 1;
      return node;
    }
    throw new ProgramError("PARSE", token.at);
  }
}

function parseProgram(source, maxDepth) {
  return new Parser(tokenize(source), maxDepth).parseProgram();
}

module.exports = { ProgramError, parseDocument, parseProgram, tokenize };
