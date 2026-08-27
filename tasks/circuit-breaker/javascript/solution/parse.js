"use strict";

const TOP_LEVEL = ["calls", "config"];
const CONFIG_KEYS = ["cooldownMs", "failureStatuses", "halfOpenLimit", "threshold"];
const CALL_KEYS = ["at", "outcome", "target"];
const TARGET = /^[A-Za-z0-9_.-]+$/;

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasKeys(value, keys) {
  return Object.keys(value).sort().join(",") === keys.join(",");
}

function isInteger(value) {
  return typeof value === "number" && Number.isInteger(value);
}

function isStatus(value) {
  return isInteger(value) && value >= 100 && value <= 599;
}

function parseDocument(value) {
  if (!isObject(value) || !hasKeys(value, TOP_LEVEL)) {
    throw new Error("malformed document");
  }
  if (!Array.isArray(value.calls)) {
    throw new Error("malformed calls");
  }
  return value;
}

function parseConfig(value) {
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
  const statuses = new Set(failureStatuses);
  if (statuses.size !== failureStatuses.length) {
    throw new Error("duplicate failure status");
  }
  return { threshold, cooldownMs, halfOpenLimit, failureStatuses: statuses };
}

function parseCall(value, previous) {
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
function classify(outcome, failureStatuses) {
  if (!isObject(outcome) || !("kind" in outcome)) {
    throw new Error("malformed outcome");
  }
  const kind = outcome.kind;
  if (kind === "ok" || kind === "error") {
    if (!hasKeys(outcome, ["kind"])) {
      throw new Error("malformed outcome");
    }
    return kind === "ok" ? "success" : "failure";
  }
  if (kind === "status") {
    if (!hasKeys(outcome, ["kind", "status"])) {
      throw new Error("malformed outcome");
    }
    if (!isStatus(outcome.status)) {
      throw new Error("malformed status");
    }
    return failureStatuses.has(outcome.status) ? "failure" : "neutral";
  }
  throw new Error("unknown outcome kind");
}

module.exports = { classify, parseCall, parseConfig, parseDocument };
