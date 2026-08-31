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

const BINARY_LEVELS: string[][] = [
  ["|"],
  ["^"],
  ["&"],
  ["==", "!="],
  ["<", "<=", ">", ">="],
  ["<<", ">>"],
  ["+", "-"],
  ["*", "/", "%"],
];

export type Token =
  | { kind: "int"; value: bigint; at: number }
  | { kind: "ident"; text: string; at: number }
  | { kind: "let"; at: number }
  | { kind: "operator"; text: string; at: number }
  | { kind: "end"; at: number };

export type Node =
  | { kind: "literal"; value: bigint; at: number }
  | { kind: "name"; name: string; at: number }
  | { kind: "unary"; operator: string; operand: Node; at: number }
  | { kind: "binary"; operator: string; left: Node; right: Node; at: number };

export interface Binding {
  name: string;
  node: Node;
}

export interface Program {
  bindings: Binding[];
  body: Node;
}

export interface Source {
  id: string;
  source: string;
}

export interface Document {
  maxDepth: number;
  programs: Source[];
}

/** A fault in one program's source, reported instead of a value. */
export class ProgramError extends Error {
  readonly code: string;
  readonly at: number;

  constructor(code: string, at: number) {
    super(code);
    this.code = code;
    this.at = at;
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return Object.keys(value).sort().join(",") === keys.join(",");
}

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

export function parseDocument(value: unknown): Document {
  if (!isObject(value) || !hasKeys(value, TOP_LEVEL)) {
    throw new Error("malformed document");
  }
  const config = value["config"];
  if (!isObject(config) || !hasKeys(config, CONFIG_KEYS)) {
    throw new Error("malformed config");
  }
  const maxDepth = config["maxDepth"];
  if (!isInteger(maxDepth) || maxDepth < 1) {
    throw new Error("malformed maxDepth");
  }
  const raw = value["programs"];
  if (!Array.isArray(raw)) {
    throw new Error("malformed programs");
  }
  const seen = new Set<string>();
  const programs: Source[] = [];
  for (const item of raw) {
    if (!isObject(item) || !hasKeys(item, PROGRAM_KEYS)) {
      throw new Error("malformed program");
    }
    const id = item["id"];
    const source = item["source"];
    if (typeof id !== "string" || !PROGRAM_ID.test(id)) {
      throw new Error("malformed id");
    }
    if (seen.has(id)) {
      throw new Error("duplicate id");
    }
    if (typeof source !== "string") {
      throw new Error("malformed source");
    }
    seen.add(id);
    programs.push({ id, source });
  }
  return { maxDepth, programs };
}

function tokenText(token: Token): string {
  if (token.kind === "operator" || token.kind === "ident") {
    return token.text;
  }
  return token.kind;
}

/** Source as a list of tokens, with offsets counted in code points. */
export function tokenize(source: string): Token[] {
  const points = Array.from(source);
  const tokens: Token[] = [];
  let index = 0;
  while (index < points.length) {
    const character = points[index] as string;
    if (character === " " || character === "\t" || character === "\r" || character === "\n") {
      index += 1;
      continue;
    }
    if (DIGIT.test(character)) {
      const start = index;
      let value: bigint;
      if (
        character === "0" &&
        index + 1 < points.length &&
        (points[index + 1] === "x" || points[index + 1] === "X")
      ) {
        index += 2;
        const digits = index;
        while (index < points.length && HEX.test(points[index] as string)) {
          index += 1;
        }
        if (index === digits) {
          throw new ProgramError("PARSE", start);
        }
        value = BigInt(`0x${points.slice(digits, index).join("")}`);
      } else {
        while (index < points.length && DIGIT.test(points[index] as string)) {
          index += 1;
        }
        value = BigInt(points.slice(start, index).join(""));
      }
      if (index < points.length && IDENT_PART.test(points[index] as string)) {
        throw new ProgramError("PARSE", index);
      }
      if (value > UNSIGNED_LIMIT) {
        if (process.env["LAB_SABOTAGE"] !== "literal-range-unchecked") {
          throw new ProgramError("LITERAL_RANGE", start);
        }
        value &= UNSIGNED_LIMIT;
      }
      tokens.push({ kind: "int", value, at: start });
      continue;
    }
    if (IDENT_START.test(character)) {
      const start = index;
      while (index < points.length && IDENT_PART.test(points[index] as string)) {
        index += 1;
      }
      const text = points.slice(start, index).join("");
      tokens.push(text === "let" ? { kind: "let", at: start } : { kind: "ident", text, at: start });
      continue;
    }
    const operator = OPERATORS.find(
      (candidate) => points.slice(index, index + candidate.length).join("") === candidate,
    );
    if (operator === undefined) {
      throw new ProgramError("PARSE", index);
    }
    tokens.push({ kind: "operator", text: operator, at: index });
    index += operator.length;
  }
  tokens.push({ kind: "end", at: points.length });
  return tokens;
}

class Parser {
  private readonly tokens: Token[];
  private readonly maxDepth: number;
  private readonly levels: string[][];
  private index = 0;
  private depth = 0;

  constructor(tokens: Token[], maxDepth: number) {
    this.tokens = tokens;
    this.maxDepth = maxDepth;
    this.levels = BINARY_LEVELS.map((level) => level);
    if (process.env["LAB_SABOTAGE"] === "precedence-additive-first") {
      const last = this.levels.length - 1;
      const swap = this.levels[last] as string[];
      this.levels[last] = this.levels[last - 1] as string[];
      this.levels[last - 1] = swap;
    }
  }

  private peek(): Token {
    return this.tokens[this.index] as Token;
  }

  private take(): Token {
    const token = this.peek();
    this.index += 1;
    return token;
  }

  private isOperator(token: Token, level: string[]): boolean {
    return token.kind === "operator" && level.includes(token.text);
  }

  parseProgram(): Program {
    const bindings: Binding[] = [];
    while (this.peek().kind === "let") {
      this.take();
      const name = this.peek();
      if (name.kind !== "ident") {
        throw new ProgramError("PARSE", name.at);
      }
      this.take();
      const assign = this.peek();
      if (!this.isOperator(assign, ["="])) {
        throw new ProgramError("PARSE", assign.at);
      }
      this.take();
      bindings.push({ name: name.text, node: this.parseExpression(0) });
      const semicolon = this.peek();
      if (!this.isOperator(semicolon, [";"])) {
        throw new ProgramError("PARSE", semicolon.at);
      }
      this.take();
    }
    const body = this.parseExpression(0);
    const trailing = this.peek();
    if (trailing.kind !== "end") {
      throw new ProgramError("PARSE", trailing.at);
    }
    return { bindings, body };
  }

  private parseExpression(level: number): Node {
    if (level >= this.levels.length) {
      return this.parseUnary();
    }
    let node = this.parseExpression(level + 1);
    while (this.isOperator(this.peek(), this.levels[level] as string[])) {
      const operator = this.take();
      const right = this.parseExpression(level + 1);
      node = { kind: "binary", operator: tokenText(operator), left: node, right, at: operator.at };
    }
    return node;
  }

  private parseUnary(): Node {
    const token = this.peek();
    if (this.isOperator(token, ["-", "~"])) {
      this.take();
      return {
        kind: "unary",
        operator: tokenText(token),
        operand: this.parseUnary(),
        at: token.at,
      };
    }
    return this.parsePrimary();
  }

  private parsePrimary(): Node {
    const token = this.peek();
    if (token.kind === "int") {
      this.take();
      return { kind: "literal", value: token.value, at: token.at };
    }
    if (token.kind === "ident") {
      this.take();
      return { kind: "name", name: token.text, at: token.at };
    }
    if (this.isOperator(token, ["("])) {
      this.depth += 1;
      if (this.depth > this.maxDepth) {
        throw new ProgramError("DEPTH", token.at);
      }
      this.take();
      const node = this.parseExpression(0);
      const closing = this.peek();
      if (!this.isOperator(closing, [")"])) {
        throw new ProgramError("PARSE", closing.at);
      }
      this.take();
      this.depth -= 1;
      return node;
    }
    throw new ProgramError("PARSE", token.at);
  }
}

export function parseProgram(source: string, maxDepth: number): Program {
  return new Parser(tokenize(source), maxDepth).parseProgram();
}
