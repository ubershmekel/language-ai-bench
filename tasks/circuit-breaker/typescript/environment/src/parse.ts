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
  outcome: CallOutcome;
}

export interface Config {
  threshold: number;
  cooldownMs: number;
  halfOpenLimit: number;
  failureStatuses: number[];
}

export interface Document {
  config: Config;
  calls: Call[];
}

const TOP_LEVEL = ["calls", "config"];

/**
 * Accept the parsed input as a run description. The current implementation
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
    threshold: value.threshold,
    cooldownMs: value.cooldownMs,
    halfOpenLimit: value.halfOpenLimit,
    failureStatuses: value.failureStatuses,
  };
}

/** Every outcome that is not a success counts as a failure. */
export function classify(
  outcome: CallOutcome,
  failureStatuses: number[],
): Outcome {
  return outcome.kind === "ok" ? "success" : "failure";
}
