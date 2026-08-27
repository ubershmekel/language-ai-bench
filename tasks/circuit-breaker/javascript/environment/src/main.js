"use strict";

const { admit, newBreaker, observe, record } = require("./breaker");
const { classify, parseConfig, parseDocument } = require("./parse");

function run(value) {
  const document = parseDocument(value);
  const config = parseConfig(document.config);
  const breaker = newBreaker();
  const seen = [];
  const decisions = [];
  for (const call of document.calls) {
    const target = call.target;
    if (!seen.includes(target)) {
      seen.push(target);
    }
    const observed = observe(breaker, call.at, config);
    if (!admit(breaker, observed, config)) {
      decisions.push({
        target,
        state: observed,
        admitted: false,
        recorded: "rejected",
      });
      continue;
    }
    const outcome = classify(call.outcome, config.failureStatuses);
    record(breaker, observed, outcome, call.at, config);
    decisions.push({
      target,
      state: observed,
      admitted: true,
      recorded: outcome,
    });
  }
  return {
    decisions,
    targets: seen.map((name) => ({
      target: name,
      state: breaker.state,
      failures: breaker.failures,
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
