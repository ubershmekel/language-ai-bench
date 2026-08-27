"use strict";

const TOP_LEVEL = ["calls", "config"];

/**
 * Accept the parsed input as a run description. The current implementation
 * checks only the top-level key set and trusts every value below it.
 */
function parseDocument(value) {
  const keys = Object.keys(value ?? {})
    .sort()
    .join(",");
  if (keys !== TOP_LEVEL.join(",")) {
    throw new Error("malformed document");
  }
  return value;
}

function parseConfig(value) {
  return {
    threshold: value.threshold,
    cooldownMs: value.cooldownMs,
    halfOpenLimit: value.halfOpenLimit,
    failureStatuses: value.failureStatuses,
  };
}

/** Every outcome that is not a success counts as a failure. */
function classify(outcome, failureStatuses) {
  return outcome.kind === "ok" ? "success" : "failure";
}

module.exports = { classify, parseConfig, parseDocument };
