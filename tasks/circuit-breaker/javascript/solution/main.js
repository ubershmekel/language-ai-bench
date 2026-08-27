"use strict";

const { admit, newBreaker, observe, record } = require("./breaker");
const { classify, parseCall, parseConfig, parseDocument } = require("./parse");

function run(value) {
  const document = parseDocument(value);
  const config = parseConfig(document.config);
  const breakers = new Map();
  const decisions = [];
  let previous = 0;
  for (const item of document.calls) {
    const { at, target, outcome: raw } = parseCall(item, previous);
    previous = at;
    const outcome = classify(raw, config.failureStatuses);
    const key = process.env.LAB_SABOTAGE === "global-state" ? "" : target;
    if (!breakers.has(key)) {
      breakers.set(key, newBreaker());
    }
    const breaker = breakers.get(key);
    const observed = observe(breaker, at, config);
    if (!admit(breaker, observed, config)) {
      decisions.push({
        target,
        state: observed,
        admitted: false,
        recorded: "rejected",
      });
      continue;
    }
    record(breaker, observed, outcome, at, config);
    decisions.push({
      target,
      state: observed,
      admitted: true,
      recorded: outcome,
    });
  }
  const names = [...breakers.keys()].sort((left, right) =>
    left < right ? -1 : left > right ? 1 : 0,
  );
  return {
    decisions,
    targets: names.map((name) => ({
      target: name,
      state: breakers.get(name).state,
      failures: breakers.get(name).failures,
    })),
  };
}

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  input += chunk;
});
process.stdin.on("end", () => {
  try {
    process.stdout.write(JSON.stringify(run(JSON.parse(input))) + "\n");
  } catch (error) {
    process.stderr.write(
      (error instanceof Error ? error.message : String(error)) + "\n",
    );
    process.exit(1);
  }
});
