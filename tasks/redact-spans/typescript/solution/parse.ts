export type Policy = "merge" | "strict";

export interface LiteralRule {
  id: string;
  kind: "literal";
  value: string;
}

export interface SpanRule {
  id: string;
  kind: "span";
  start: number;
  end: number;
}

export type Rule = LiteralRule | SpanRule;

export interface Config {
  mask: string;
  policy: Policy;
  minLength: number;
}

export interface Document {
  config: unknown;
  text: string;
  rules: unknown[];
}

export interface Span {
  start: number;
  end: number;
  rules: string[];
}

const TOP_LEVEL = ["config", "rules", "text"];
const CONFIG_KEYS = ["mask", "minLength", "policy"];
const LITERAL_KEYS = ["id", "kind", "value"];
const SPAN_KEYS = ["end", "id", "kind", "start"];
const POLICIES: Policy[] = ["merge", "strict"];
const RULE_ID = /^[A-Za-z0-9_.-]+$/;

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return Object.keys(value).sort().join(",") === keys.join(",");
}

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

/** The text as an array of Unicode code points. */
export function codePoints(text: string): string[] {
  return Array.from(text);
}

export function parseDocument(value: unknown): Document {
  if (!isObject(value) || !hasKeys(value, TOP_LEVEL)) {
    throw new Error("malformed document");
  }
  if (typeof value.text !== "string") {
    throw new Error("malformed text");
  }
  if (!Array.isArray(value.rules)) {
    throw new Error("malformed rules");
  }
  return { config: value.config, text: value.text, rules: value.rules };
}

export function parseConfig(value: unknown): Config {
  if (!isObject(value) || !hasKeys(value, CONFIG_KEYS)) {
    throw new Error("malformed config");
  }
  const { mask, policy, minLength } = value;
  if (typeof mask !== "string" || codePoints(mask).length !== 1) {
    throw new Error("malformed mask");
  }
  if (typeof policy !== "string" || !POLICIES.includes(policy as Policy)) {
    throw new Error("malformed policy");
  }
  if (!isInteger(minLength) || minLength < 1) {
    throw new Error("malformed minimum length");
  }
  return { mask, policy: policy as Policy, minLength };
}

export function parseRule(
  value: unknown,
  seen: Set<string>,
  length: number,
): Rule {
  if (!isObject(value) || !("kind" in value)) {
    throw new Error("malformed rule");
  }
  const id = value.id;
  if (typeof id !== "string" || !RULE_ID.test(id)) {
    throw new Error("malformed rule id");
  }
  if (seen.has(id)) {
    throw new Error("duplicate rule id");
  }
  if (value.kind === "literal") {
    if (!hasKeys(value, LITERAL_KEYS)) {
      throw new Error("malformed literal rule");
    }
    if (typeof value.value !== "string" || value.value.length === 0) {
      throw new Error("malformed literal value");
    }
    return { id, kind: "literal", value: value.value };
  }
  if (value.kind === "span") {
    if (!hasKeys(value, SPAN_KEYS)) {
      throw new Error("malformed span rule");
    }
    const { start, end } = value;
    if (!isInteger(start) || !isInteger(end) || start < 0) {
      throw new Error("malformed span bounds");
    }
    if (start >= end || end > length) {
      throw new Error("malformed span bounds");
    }
    return { id, kind: "span", start, end };
  }
  throw new Error("unknown rule kind");
}
