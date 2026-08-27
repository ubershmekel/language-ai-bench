import type { Config, Outcome, State } from "./parse";

export interface Breaker {
  state: State;
  failures: number;
  openedAt: number;
  probes: number;
}

const sabotage = process.env.LAB_SABOTAGE ?? "";

export function newBreaker(): Breaker {
  return { state: "closed", failures: 0, openedAt: 0, probes: 0 };
}

/** Advance an expired open breaker, then report the state the call sees. */
export function observe(breaker: Breaker, at: number, config: Config): State {
  if (breaker.state === "open") {
    const elapsed = at - breaker.openedAt;
    const ready =
      sabotage === "cooldown-off-by-one"
        ? elapsed > config.cooldownMs
        : elapsed >= config.cooldownMs;
    if (ready) {
      breaker.state = "half-open";
      breaker.probes = 0;
    }
  }
  return breaker.state;
}

export function admit(
  breaker: Breaker,
  observed: State,
  config: Config,
): boolean {
  if (observed === "open") return false;
  if (observed !== "half-open") return true;
  if (sabotage === "no-half-open-limit") return true;
  return breaker.probes < config.halfOpenLimit;
}

export function record(
  breaker: Breaker,
  observed: State,
  outcome: Outcome,
  at: number,
  config: Config,
): void {
  if (observed === "half-open") {
    breaker.probes += 1;
  }
  let effective: Outcome = outcome;
  if (sabotage === "neutral-counts-as-success" && outcome === "neutral") {
    effective = "success";
  }
  if (effective === "neutral") return;
  if (effective === "success") {
    breaker.failures = 0;
    if (observed === "half-open") {
      breaker.state = "closed";
    }
    return;
  }
  breaker.failures += 1;
  if (observed === "half-open" || breaker.failures >= config.threshold) {
    breaker.state = "open";
    breaker.openedAt = at;
  }
}
