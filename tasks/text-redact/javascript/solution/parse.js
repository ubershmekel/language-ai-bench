"use strict";

const TOP_LEVEL = ["config", "rules", "text"];
const CONFIG_KEYS = ["mask", "minLength", "policy"];
const LITERAL_KEYS = ["id", "kind", "value"];
const SPAN_KEYS = ["end", "id", "kind", "start"];
const POLICIES = ["merge", "strict"];
const RULE_ID = /^[A-Za-z0-9_.-]+$/;

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasKeys(value, keys) {
  return Object.keys(value).sort().join(",") === keys.join(",");
}

function isInteger(value) {
  return typeof value === "number" && Number.isInteger(value);
}

/** The text as an array of Unicode code points. */
function codePoints(text) {
  return Array.from(text);
}

function parseDocument(value) {
  if (!isObject(value) || !hasKeys(value, TOP_LEVEL)) {
    throw new Error("malformed document");
  }
  if (typeof value.text !== "string") {
    throw new Error("malformed text");
  }
  if (!Array.isArray(value.rules)) {
    throw new Error("malformed rules");
  }
  return value;
}

function parseConfig(value) {
  if (!isObject(value) || !hasKeys(value, CONFIG_KEYS)) {
    throw new Error("malformed config");
  }
  const { mask, policy, minLength } = value;
  if (typeof mask !== "string" || codePoints(mask).length !== 1) {
    throw new Error("malformed mask");
  }
  if (typeof policy !== "string" || !POLICIES.includes(policy)) {
    throw new Error("malformed policy");
  }
  if (!isInteger(minLength) || minLength < 1) {
    throw new Error("malformed minimum length");
  }
  return { mask, policy, minLength };
}

function parseRule(value, seen, length) {
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

module.exports = { codePoints, parseConfig, parseDocument, parseRule };
