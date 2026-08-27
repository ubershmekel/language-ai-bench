import type { Config, Outcome, State } from "./parse";

export interface Breaker {
  state: State;
  failures: number;
  openedAt: number;
  probes: number;
}

export function newBreaker(): Breaker {
  return { state: "closed", failures: 0, openedAt: 0, probes: 0 };
}

/** The state the breaker is in when a call arrives. */
export function observe(breaker: Breaker, at: number, config: Config): State {
  return breaker.state;
}

export function admit(
  breaker: Breaker,
  observed: State,
  config: Config,
): boolean {
  return observed !== "open";
}

export function record(
  breaker: Breaker,
  observed: State,
  outcome: Outcome,
  at: number,
  config: Config,
): void {
  if (outcome === "success") {
    breaker.failures = 0;
    return;
  }
  breaker.failures += 1;
  if (breaker.failures >= config.threshold) {
    breaker.state = "open";
    breaker.openedAt = at;
  }
}
