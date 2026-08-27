export type State = "closed" | "open" | "half-open";
export type Outcome = "success" | "failure" | "neutral";
export type Recorded = Outcome | "rejected";

export type CallOutcome =
  | { kind: "ok" }
  | { kind: "error" }
  | { kind: "status"; status: number };

export interface Call {
  at: number;
  target: string;
  outcome: unknown;
}

export interface Config {
  threshold: number;
  cooldownMs: number;
  halfOpenLimit: number;
  failureStatuses: Set<number>;
}

export interface Document {
  config: unknown;
  calls: unknown[];
}

const TOP_LEVEL = ["calls", "config"];
const CONFIG_KEYS = [
  "cooldownMs",
  "failureStatuses",
  "halfOpenLimit",
  "threshold",
];
const CALL_KEYS = ["at", "outcome", "target"];
const TARGET = /^[A-Za-z0-9_.-]+$/;

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return Object.keys(value).sort().join(",") === keys.join(",");
}

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function isStatus(value: unknown): value is number {
  return isInteger(value) && value >= 100 && value <= 599;
}

export function parseDocument(value: unknown): Document {
  if (!isObject(value) || !hasKeys(value, TOP_LEVEL)) {
    throw new Error("malformed document");
  }
  if (!Array.isArray(value.calls)) {
    throw new Error("malformed calls");
  }
  return { config: value.config, calls: value.calls };
}

export function parseConfig(value: unknown): Config {
  if (!isObject(value) || !hasKeys(value, CONFIG_KEYS)) {
    throw new Error("malformed config");
  }
  const { threshold, cooldownMs, halfOpenLimit, failureStatuses } = value;
  if (!isInteger(threshold) || threshold < 1) {
    throw new Error("malformed threshold");
  }
  if (!isInteger(cooldownMs) || cooldownMs < 0) {
    throw new Error("malformed cooldown");
  }
  if (!isInteger(halfOpenLimit) || halfOpenLimit < 1) {
    throw new Error("malformed half-open limit");
  }
  if (!Array.isArray(failureStatuses) || !failureStatuses.every(isStatus)) {
    throw new Error("malformed failure statuses");
  }
  const statuses = new Set<number>(failureStatuses);
  if (statuses.size !== failureStatuses.length) {
    throw new Error("duplicate failure status");
  }
  return { threshold, cooldownMs, halfOpenLimit, failureStatuses: statuses };
}

export function parseCall(value: unknown, previous: number): Call {
  if (!isObject(value) || !hasKeys(value, CALL_KEYS)) {
    throw new Error("malformed call");
  }
  const { at, target } = value;
  if (!isInteger(at) || at < 0 || at < previous) {
    throw new Error("malformed timestamp");
  }
  if (typeof target !== "string" || !TARGET.test(target)) {
    throw new Error("malformed target");
  }
  return { at, target, outcome: value.outcome };
}

/** Sort an outcome into a success, a failure, or a neutral result. */
export function classify(
  value: unknown,
  failureStatuses: Set<number>,
): Outcome {
  if (!isObject(value) || !("kind" in value)) {
    throw new Error("malformed outcome");
  }
  const kind = value.kind;
  if (kind === "ok" || kind === "error") {
    if (!hasKeys(value, ["kind"])) {
      throw new Error("malformed outcome");
    }
    return kind === "ok" ? "success" : "failure";
  }
  if (kind === "status") {
    if (!hasKeys(value, ["kind", "status"])) {
      throw new Error("malformed outcome");
    }
    if (!isStatus(value.status)) {
      throw new Error("malformed status");
    }
    return failureStatuses.has(value.status) ? "failure" : "neutral";
  }
  throw new Error("unknown outcome kind");
}
