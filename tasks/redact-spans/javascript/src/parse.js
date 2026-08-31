"use strict";

const TOP_LEVEL = ["config", "rules", "text"];

/**
 * Accept the parsed input as a redaction request. The current implementation
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
    mask: value.mask,
    policy: value.policy,
    minLength: value.minLength,
  };
}

/** Only literal rules are understood so far. */
function parseRule(value, seen, length) {
  if (value.kind !== "literal") {
    throw new Error("unsupported rule kind");
  }
  return { id: value.id, kind: "literal", value: value.value };
}

module.exports = { parseConfig, parseDocument, parseRule };
