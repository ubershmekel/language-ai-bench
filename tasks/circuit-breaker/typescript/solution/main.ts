import { admit, newBreaker, observe, record } from "./breaker";
import type { Breaker } from "./breaker";
import { classify, parseCall, parseConfig, parseDocument } from "./parse";
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
  const breakers = new Map<string, Breaker>();
  const decisions: Decision[] = [];
  let previous = 0;
  for (const item of document.calls) {
    const call = parseCall(item, previous);
    previous = call.at;
    const outcome = classify(call.outcome, config.failureStatuses);
    const key = process.env.LAB_SABOTAGE === "global-state" ? "" : call.target;
    let breaker = breakers.get(key);
    if (!breaker) {
      breaker = newBreaker();
      breakers.set(key, breaker);
    }
    const observed = observe(breaker, call.at, config);
    if (!admit(breaker, observed, config)) {
      decisions.push({
        target: call.target,
        state: observed,
        admitted: false,
        recorded: "rejected",
      });
      continue;
    }
    record(breaker, observed, outcome, call.at, config);
    decisions.push({
      target: call.target,
      state: observed,
      admitted: true,
      recorded: outcome,
    });
  }
  const entries = [...breakers.entries()].sort(([left], [right]) =>
    left < right ? -1 : left > right ? 1 : 0,
  );
  return {
    decisions,
    targets: entries.map(([name, breaker]) => ({
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
