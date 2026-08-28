# Language AI Bench v0.9: the new family was too easy, and the old ones moved

## What this cohort was for

v0.8 ran two families hard enough to discriminate and they ranked the
five arms in nearly opposite orders. Each ordering followed from what the
family rewards. Two families cannot say whether that is a pattern or a
coincidence, so v0.9 added a third that turns on a third thing.

| Family | What it rewards |
|---|---|
| `circuit-breaker` | not dropping a case of a union that crosses files |
| `money-rollup` | exact rational arithmetic in the standard library |
| `text-redact` | knowing what a string is at runtime |

`text-redact` specifies every offset and length in Unicode code points.
Python indexes code points already. JavaScript and TypeScript index
UTF-16 code units, so an emoji counts as two. Go indexes bytes, so the
same emoji counts as four. `tsc` and `mypy` report nothing about the
difference, because `string` is `string` whichever unit you meant, while
`go build` forces `string` and `[]rune` apart at every boundary.

**120 rollouts, $0.699961 measured spend.**

## Headline: it did not work

`text-redact` passed 39 of 40 across the five arms, so it cannot rank them. Worse for the hypothesis it was built to test, the code point hazard never fired: of those 40 runs, 0 failed either of the two hidden cases that catch offsets counted in UTF-16 code units or bytes.

The likely cause is a task-design mistake and it is worth naming
precisely. The instruction states the code point rule in its own
paragraph and adds that it does not matter how your language happens to
index a string. That is a loud warning sitting directly on the hazard,
so every arm converted to a code point array up front and the trap was
never sprung. The rule has to be stated somewhere, but it did not need a
paragraph of its own, and the two developer tests could have been ASCII
only with the astral cases left entirely hidden. That is the fix for a
v1.0 revision, and it is a change to the task, not to this result.

## Results by family

This is the estimand. The pooled table further down is not.

| Family | Spread | Ordering |
|---|---:|---|
| `circuit-breaker` | 4 runs | JavaScript 6/8 > Go 4/8 > Python (typed) 4/8 > Python 2/8 > TypeScript 2/8 |
| `money-rollup` | 3 runs | Python (typed) 7/8 > Python 6/8 > TypeScript 6/8 > JavaScript 5/8 > Go 4/8 |
| `text-redact` | 1 run | Go 8/8 > Python 8/8 > Python (typed) 8/8 > TypeScript 8/8 > JavaScript 7/8 |

A family counts as discriminating here only if its best and worst arms differ by at least 2 runs out of eight. One run of separation is not an ordering, and treating it as one manufactures reversals out of noise.

## Does any language lead everywhere?

`text-redact` is flat across the arms by that test and contributes no
correctness signal, so the question is answered by the two families
carried over from v0.8.

No. No language is top on both families that discriminate, and none
is bottom on both. The v0.8 disagreement reproduced in the sense that
the two families still disagree.

## How much the ordering moved since v0.8

Same tasks, same model, same scaffold, same eight attempts per cell,
a different randomization seed. This is the most useful number in the
report, because it bounds how much weight any single ordering can
carry.

| Family | Arm | v0.8 | v0.9 | Change |
|---|---|---:|---:|---:|
| circuit-breaker | Go | 7/8 | 4/8 | -3 |
| circuit-breaker | JavaScript | 4/8 | 6/8 | +2 |
| circuit-breaker | Python | 2/8 | 2/8 | +0 |
| circuit-breaker | Python (typed) | 3/8 | 4/8 | +1 |
| circuit-breaker | TypeScript | 6/8 | 2/8 | -4 |
| money-rollup | Go | 6/8 | 4/8 | -2 |
| money-rollup | JavaScript | 5/8 | 5/8 | +0 |
| money-rollup | Python | 8/8 | 6/8 | -2 |
| money-rollup | Python (typed) | 8/8 | 7/8 | -1 |
| money-rollup | TypeScript | 6/8 | 6/8 | +0 |

The largest single move is TypeScript on `circuit-breaker`, -4 runs out of eight, with nothing changed but the seed. Eight attempts per cell is
not enough to fix a per-family ordering, and any reading of these
tables that treats the exact order as stable is reading noise. What
survives across both cohorts is the weaker and more useful claim:
the families disagree, and no arm leads on all of them.

## Counting the offsets in the wrong unit

Two `text-redact` hidden cases fail specifically when the offsets are
counted in UTF-16 code units or bytes rather than code points:
`code-point-offsets` and `astral-mask`. Every other failure mode leaves
them alone. This is the mechanism the family was built to expose, and it
did not appear once.

| Arm | Runs | Runs failing a code point case | Rate |
|---|---:|---:|---:|
| JavaScript | 8 | 0 | 0.00 |
| TypeScript | 8 | 0 | 0.00 |
| Python | 8 | 0 | 0.00 |
| Python (typed) | 8 | 0 | 0.00 |
| Go | 8 | 0 | 0.00 |

## Results by family and arm

| Family | Arm | Passed | Pass rate | Mean steps |
|---|---|---:|---:|---:|
| circuit-breaker | Go | 4/8 | 0.50 | 6.62 |
| circuit-breaker | JavaScript | 6/8 | 0.75 | 5.62 |
| circuit-breaker | Python | 2/8 | 0.25 | 5.62 |
| circuit-breaker | Python (typed) | 4/8 | 0.50 | 6.75 |
| circuit-breaker | TypeScript | 2/8 | 0.25 | 6.12 |
| money-rollup | Go | 4/8 | 0.50 | 8.25 |
| money-rollup | JavaScript | 5/8 | 0.62 | 6.88 |
| money-rollup | Python | 6/8 | 0.75 | 6.00 |
| money-rollup | Python (typed) | 7/8 | 0.88 | 7.25 |
| money-rollup | TypeScript | 6/8 | 0.75 | 8.50 |
| text-redact | Go | 8/8 | 1.00 | 8.50 |
| text-redact | JavaScript | 7/8 | 0.88 | 5.38 |
| text-redact | Python | 8/8 | 1.00 | 5.88 |
| text-redact | Python (typed) | 8/8 | 1.00 | 6.25 |
| text-redact | TypeScript | 8/8 | 1.00 | 6.12 |

## Pooled across all three families

Reported for completeness. Pooling families that disagree produces a
number that describes none of them, which is the whole point above.

| Arm | Passed | Pass rate (95% CI) | Mean steps | Mean cost |
|---|---:|---:|---:|---:|
| Go | 16/24 | 0.67 [0.47, 0.82] | 7.79 | $0.006750 |
| JavaScript | 18/24 | 0.75 [0.55, 0.88] | 5.96 | $0.005304 |
| Python | 16/24 | 0.67 [0.47, 0.82] | 5.83 | $0.005088 |
| Python (typed) | 19/24 | 0.79 [0.60, 0.91] | 6.75 | $0.005851 |
| TypeScript | 16/24 | 0.67 [0.47, 0.82] | 6.92 | $0.006173 |

## Contrasts whose interval excludes zero

- JavaScript needed 0.96 fewer agent steps than TypeScript (95% CI [-1.875, -0.208])
- JavaScript needed 0.79 fewer agent steps than Python (typed) (95% CI [-1.292, -0.292])
- JavaScript needed 1.83 fewer agent steps than Go (95% CI [-2.792, -0.917])
- TypeScript needed 1.08 more agent steps than Python (95% CI [0.417, 1.958])
- Python needed 0.92 fewer agent steps than Python (typed) (95% CI [-1.458, -0.417])
- Python needed 1.96 fewer agent steps than Go (95% CI [-2.875, -1.125])
- Python (typed) needed 1.04 fewer agent steps than Go (95% CI [-2.084, -0.042])

These are pooled over the three families and inherit the same warning:
a pooled contrast between two arms is an average over tasks that
disagree about the ordering.

## Failing verifier cases

| Arm | Failing cases |
|---|---|
| Go | rejects-invalid x4, half-open-limit x3, cooldown-boundary x2, half-open-closes x2, half-open-reopens x2, neutral-not-counted x1, neutral-does-not-reset x1, streak-resets x1, chained-conversion x1, shortest-path-preferred x1, half-even-ties x1, per-entry-rounding x1, exact-large-magnitude x1, zero-and-negative-formatting x1, empty-entries x1 |
| JavaScript | rejects-invalid x4, cooldown-boundary x2, half-open-closes x2, half-open-reopens x2, half-open-limit x2 |
| Python | cooldown-boundary x6, half-open-closes x6, half-open-reopens x6, half-open-limit x6, shortest-path-preferred x1, half-even-ties x1, per-entry-rounding x1 |
| Python (typed) | cooldown-boundary x4, half-open-closes x4, half-open-reopens x4, half-open-limit x4, half-even-ties x1, zero-and-negative-formatting x1 |
| TypeScript | cooldown-boundary x6, half-open-closes x6, half-open-reopens x6, half-open-limit x6, regression-flat-accounts x1, ancestor-rollup x1, chained-conversion x1, shortest-path-preferred x1, half-even-ties x1, per-entry-rounding x1, exact-large-magnitude x1, zero-and-negative-formatting x1, prefix-sorting x1, empty-entries x1, target-ordering x1, rejects-invalid x1 |

## Scope and limits

Three brownfield families, five arms, eight attempts per cell, one model
rung, one bash-only scaffold. Three families is still below the point
where between-family variance is well estimated, so this supports claims
about these three tasks and no language-general claim.

The stopping rule was fixed at 120 rollouts before the first paid call
and no interim analysis informed continuation. v0.7's second batch was
run because the first left an interval touching zero, which made that
continuation outcome-dependent; this design does not repeat it.

`text-redact` had never been run against a model before this cohort. Its
difficulty was calibrated only in the free sense: the gate is green and
the starter fails ten of the twelve checks. That is not the same as
landing in the 40 to 60 percent band the design targets, and it did not.
The result is reported as it came out rather than adjusted afterwards,
and the forty rollouts it cost are the price of finding out. The design
already says difficulty and model tier have to be calibrated jointly; a
green gate is necessary and is plainly not sufficient.

Agent wall time is not reported. This cohort ran four rollouts at a time,
so elapsed time includes contention. All three families are command-mode,
so no timing-sensitive verifier case was exposed to it.

The families were chosen to reward different things, so their
disagreement is partly by construction. That is the point: it shows the
ordering is a property of the task, not of the language. It does not show
how often real tickets look like any one of these three.

