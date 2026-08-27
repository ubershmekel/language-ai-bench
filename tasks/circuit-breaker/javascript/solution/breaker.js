"use strict";

const sabotage = process.env.LAB_SABOTAGE || "";

function newBreaker() {
  return { state: "closed", failures: 0, openedAt: 0, probes: 0 };
}

/** Advance an expired open breaker, then report the state the call sees. */
function observe(breaker, at, config) {
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

function admit(breaker, observed, config) {
  if (observed === "open") return false;
  if (observed !== "half-open") return true;
  if (sabotage === "no-half-open-limit") return true;
  return breaker.probes < config.halfOpenLimit;
}

function record(breaker, observed, outcome, at, config) {
  if (observed === "half-open") {
    breaker.probes += 1;
  }
  let effective = outcome;
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
  if (observed === "half-open") {
    breaker.state = "open";
    breaker.openedAt = at;
  } else if (breaker.failures >= config.threshold) {
    breaker.state = "open";
    breaker.openedAt = at;
  }
}

module.exports = { admit, newBreaker, observe, record };
