# Make the circuit breaker honour every state transition

The supplied project contains a command-line circuit-breaker simulator. It reads
one JSON object from standard input and writes the result as JSON to standard
output. The current implementation keeps a single global failure count, never
recovers, and validates almost nothing. Rework it so it satisfies the contract
below.

## Input

```json
{
  "config": {
    "threshold": 2,
    "cooldownMs": 100,
    "halfOpenLimit": 1,
    "failureStatuses": [500, 503]
  },
  "calls": [
    {"at": 0, "target": "alpha", "outcome": {"kind": "status", "status": 500}},
    {"at": 10, "target": "alpha", "outcome": {"kind": "error"}},
    {"at": 20, "target": "alpha", "outcome": {"kind": "ok"}}
  ]
}
```

`at` is a millisecond timestamp. `target` names the resource the call is made
against. Each call is offered to the breaker in the order given.

## Required behavior

**Per-target state.** Every `target` has its own breaker. Targets never affect
one another. A target is first seen in the `closed` state with a failure streak
of zero.

**Outcome classification.** Each outcome is exactly one of three classes.
`{"kind": "ok"}` is a *success*. `{"kind": "error"}` is a *failure*. A
`{"kind": "status", "status": N}` outcome is a *failure* when `N` appears in
`failureStatuses` and is otherwise *neutral*. A neutral outcome is neither: it
must not reset a failure streak, must not count toward one, and must not change
the breaker's state.

**Admission.** A `closed` breaker admits the call. An `open` breaker rejects it
without recording an outcome. A `half-open` breaker admits at most
`halfOpenLimit` calls; once that many have been admitted since entering
`half-open`, further calls are rejected without recording an outcome.

**Transitions.** A `closed` breaker opens when its failure streak reaches
`threshold`, recording the opening call's `at` as the time it opened. An `open`
breaker becomes `half-open` on the first call whose `at` is at least
`cooldownMs` after it opened; that call is then admitted as a probe. A
`half-open` breaker closes on a success, resetting the streak to zero, and
reopens on a failure, recording that call's `at` as the new opening time. A
success in the `closed` state resets the failure streak to zero.

**Output.** Emit one decision per call in call order, then the final state of
every target sorted ascending by Unicode code point.

```json
{"decisions":[{"target":"alpha","state":"closed","admitted":true,"recorded":"failure"}],
 "targets":[{"target":"alpha","state":"closed","failures":1}]}
```

`state` is the state the breaker was in when the call was offered, before any
transition that call causes. `recorded` is `"success"`, `"failure"`,
`"neutral"`, or `"rejected"` when the call was not admitted.

**Rejection.** Exit nonzero for malformed JSON, non-object input, missing or
extra top-level keys, a `config` or `calls` value of the wrong type, missing or
extra config or call keys, a `threshold` or `halfOpenLimit` that is not an
integer of at least one, a `cooldownMs` that is not a non-negative integer, a
`failureStatuses` value that is not a list of distinct integers in 100 through
599, an `at` that is not a non-negative integer, an `at` that is less than the
previous call's `at`, a `target` that does not match `[A-Za-z0-9_.-]+`, an
unknown outcome `kind`, a `status` outcome whose `status` is not an integer in
100 through 599, and any outcome carrying keys the kind does not define.
A successful run emits only the result JSON and exits zero.

Do not add runtime dependencies or change the stdin/stdout interface. Run
`scripts/verify-local` for developer tests. Hidden tests cover per-target
isolation, cooldown boundaries, half-open probe limits, neutral outcomes,
streak resets, ordering, and rejection.
