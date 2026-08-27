"use strict";

function newBreaker() {
  return { state: "closed", failures: 0, openedAt: 0, probes: 0 };
}

/** The state the breaker is in when a call arrives. */
function observe(breaker, at, config) {
  return breaker.state;
}

function admit(breaker, observed, config) {
  return observed !== "open";
}

function record(breaker, observed, outcome, at, config) {
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

module.exports = { admit, newBreaker, observe, record };
