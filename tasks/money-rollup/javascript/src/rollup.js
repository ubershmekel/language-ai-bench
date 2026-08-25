"use strict";

function rollup(items) {
  const totals = new Map();
  for (const [account, minor] of items) {
    totals.set(account, (totals.get(account) || 0n) + minor);
  }
  return [...totals.entries()].sort((left, right) =>
    left[0] < right[0] ? -1 : left[0] > right[0] ? 1 : 0
  );
}

module.exports = { rollup };
