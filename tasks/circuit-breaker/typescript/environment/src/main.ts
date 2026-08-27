import { admit, newBreaker, observe, record } from "./breaker";
import { classify, parseConfig, parseDocument } from "./parse";
import type { Recorded, State } from "./parse";

interface Decision {
  target: string;
  state: State;
  admitted: boolean;
  recorded: Recorded;
}

interface Result {
  decisions: Decision[];
  targets: Array<{ target: string; state: State; failures: number }>;
}

export function run(value: unknown): Result {
  const document = parseDocument(value);
  const config = parseConfig(document.config);
  const breaker = newBreaker();
  const seen: string[] = [];
  const decisions: Decision[] = [];
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
process.stdin.on("data", (chunk: string) => {
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
