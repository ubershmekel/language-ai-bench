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
  config: Config;
  text: string;
  rules: Rule[];
}

export interface Span {
  start: number;
  end: number;
  rules: string[];
}

const TOP_LEVEL = ["config", "rules", "text"];

/**
 * Accept the parsed input as a redaction request. The current implementation
 * checks only the top-level key set and trusts every value below it.
 */
export function parseDocument(value: unknown): Document {
  const keys = Object.keys(value ?? {})
    .sort()
    .join(",");
  if (keys !== TOP_LEVEL.join(",")) {
    throw new Error("malformed document");
  }
  return value as Document;
}

export function parseConfig(value: Config): Config {
  return {
    mask: value.mask,
    policy: value.policy,
    minLength: value.minLength,
  };
}

/** Only literal rules are understood so far. */
export function parseRule(
  value: Rule,
  seen: Set<string>,
  length: number,
): LiteralRule {
  if (value.kind !== "literal") {
    throw new Error("unsupported rule kind");
  }
  return { id: value.id, kind: "literal", value: value.value };
}
