# Language AI Bench v0.8: does typing help, holding the language fixed?

## Why this study exists

v0.7 found Python ahead of JavaScript and Go on one hard family. That
contrast cannot separate typing from runtime, ecosystem, diagnostics, or
pretraining mass, and its failure table showed the family discriminating
on rounding mode, negative-zero formatting, and rejection coverage --
none of which a type checker sees. The untyped language sweeping such a
task is not evidence about typing.

v0.8 adds `python-typed`: the same interpreter, standard library, and
file topology as `python`, differing only in annotations and a blocking
`mypy --strict` step in the developer loop. Its paired contrast against
`python` is the only comparison in this repository whose treatment is
typing alone. It also adds `circuit-breaker`, a family whose difficulty
is routed through a state machine and an outcome union crossing module
boundaries, where a missed case is silent in JavaScript and Python and
visible to `tsc`, `go build`, and `mypy`.

**120 rollouts, $0.644634 measured spend.**

## Results by arm

| Arm | Passed | Pass rate (95% CI) | Mean steps | Mean output tokens | Mean cost |
|---|---:|---:|---:|---:|---:|
| Go | 21/24 | 0.88 [0.69, 0.96] | 6.88 | 2898 | $0.005955 |
| JavaScript | 17/24 | 0.71 [0.51, 0.85] | 5.92 | 2376 | $0.004941 |
| Python | 18/24 | 0.75 [0.55, 0.88] | 6.29 | 2400 | $0.005132 |
| Python (typed) | 19/24 | 0.79 [0.60, 0.91] | 6.75 | 2595 | $0.005247 |
| TypeScript | 20/24 | 0.83 [0.64, 0.93] | 6.67 | 2528 | $0.005586 |

## The primary contrast

Typed Python minus untyped Python on pass rate: **+0.042**, 95% CI [-0.125, 0.208] over 24 matched blocks. The interval includes zero.

On agent steps the same pair differs by **+0.46**, 95% CI [-0.17, 1.12] -- the cost side of the same treatment.

## Results by family and arm

| Family | Arm | Passed | Pass rate | Mean steps |
|---|---|---:|---:|---:|
| circuit-breaker | Go | 7/8 | 0.88 | 6.88 |
| circuit-breaker | JavaScript | 4/8 | 0.50 | 5.50 |
| circuit-breaker | Python | 2/8 | 0.25 | 6.62 |
| circuit-breaker | Python (typed) | 3/8 | 0.38 | 6.38 |
| circuit-breaker | TypeScript | 6/8 | 0.75 | 6.38 |
| configuration-merge | Go | 8/8 | 1.00 | 5.62 |
| configuration-merge | JavaScript | 8/8 | 1.00 | 5.62 |
| configuration-merge | Python | 8/8 | 1.00 | 5.88 |
| configuration-merge | Python (typed) | 8/8 | 1.00 | 6.25 |
| configuration-merge | TypeScript | 8/8 | 1.00 | 6.00 |
| money-rollup | Go | 6/8 | 0.75 | 8.12 |
| money-rollup | JavaScript | 5/8 | 0.62 | 6.62 |
| money-rollup | Python | 8/8 | 1.00 | 6.38 |
| money-rollup | Python (typed) | 8/8 | 1.00 | 7.62 |
| money-rollup | TypeScript | 6/8 | 0.75 | 7.62 |

## Where the families disagree

The design says to report per-family results in full even when they
contradict the aggregate, because disagreement across families is
itself a finding. Here it is the main one.

- **circuit-breaker**: Go 7/8 > TypeScript 6/8 > JavaScript 4/8 > Python (typed) 3/8 > Python 2/8
- **money-rollup**: Python 8/8 > Python (typed) 8/8 > Go 6/8 > TypeScript 6/8 > JavaScript 5/8

The two families that discriminate rank the arms in close to opposite
orders. Pooling them produces an aggregate that describes neither.
That is the concrete form of the warning this repository has carried
since v0.1: a single benchmark score across task families would have
hidden this completely.

configuration-merge saturated at 100% in every arm, as expected from v0.6, and contributes no correctness signal.

## Contrasts whose interval excludes zero

- JavaScript needed 0.75 fewer agent steps than TypeScript (95% CI [-1.417, -0.125])
- JavaScript needed 0.83 fewer agent steps than Python (typed) (95% CI [-1.500, -0.167])
- JavaScript needed 0.96 fewer agent steps than Go (95% CI [-1.583, -0.333])
- Python needed 0.58 fewer agent steps than Go (95% CI [-1.167, -0.042])

## Failing verifier cases

| Arm | Failing cases |
|---|---|
| Go | half-even-ties x2, regression-flat-accounts x1, ancestor-rollup x1, chained-conversion x1, shortest-path-preferred x1, per-entry-rounding x1, exact-large-magnitude x1, zero-and-negative-formatting x1, prefix-sorting x1, empty-entries x1, rejects-invalid x1 |
| JavaScript | cooldown-boundary x4, half-open-closes x4, half-open-reopens x4, half-open-limit x4, rejects-invalid x3 |
| Python | cooldown-boundary x6, half-open-closes x6, half-open-reopens x6, half-open-limit x6 |
| Python (typed) | cooldown-boundary x3, half-open-closes x3, half-open-reopens x3, half-open-limit x3, per-target-isolation x2, target-ordering x1 |
| TypeScript | half-even-ties x2, zero-and-negative-formatting x2, cooldown-boundary x2, half-open-closes x2, half-open-reopens x2, half-open-limit x2, regression-flat-accounts x1, ancestor-rollup x1, chained-conversion x1, shortest-path-preferred x1, per-entry-rounding x1, exact-large-magnitude x1, prefix-sorting x1, empty-entries x1, target-ordering x1 |

## Scope and limits

Three brownfield families, five arms, eight attempts per cell, one model
rung, one bash-only scaffold. Three families is below the point where
between-family variance dominates, so this estimates the arms at these
three tasks and supports no language-general claim.

The stopping rule was fixed at 120 rollouts before the first paid call
and no interim analysis informed continuation. v0.7's second batch was
run because the first left an interval touching zero, which made that
continuation outcome-dependent; this design does not repeat it.

Agent wall time is not reported. This cohort ran four rollouts at a time,
so elapsed time includes contention and is not comparable to v0.7's
serial figures. Correctness, steps, tokens, and cost are unaffected by
concurrency, and all three families here are command-mode, so no
timing-sensitive verifier case was exposed to it.

`python-typed` carries one asymmetry worth naming: `verify-local` runs
`mypy` before the developer tests, so a type error blocks that loop. Real
Python projects vary in whether their checker is advisory or blocking.
This arm is the blocking case, which is the stronger dose.

