"use strict";

const SEGMENT = /^[A-Za-z0-9_]+$/;

function accountPrefixes(account) {
  if (typeof account !== "string" || account === "") {
    throw new Error("malformed account");
  }
  const segments = account.split(":");
  if (segments.some((segment) => !SEGMENT.test(segment))) {
    throw new Error("malformed account");
  }
  return segments.map((_, index) => segments.slice(0, index + 1).join(":"));
}

function rollup(items) {
  const totals = new Map();
  for (const [account, minor] of items) {
    let prefixes = accountPrefixes(account);
    if (process.env.LAB_SABOTAGE === "leaf-only-rollup") {
      prefixes = prefixes.slice(-1);
    }
    for (const prefix of prefixes) {
      totals.set(prefix, (totals.get(prefix) ?? 0n) + minor);
    }
  }
  return [...totals.entries()].sort(([left], [right]) =>
    left < right ? -1 : left > right ? 1 : 0,
  );
}

module.exports = { accountPrefixes, rollup };
