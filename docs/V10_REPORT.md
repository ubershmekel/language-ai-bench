# Language AI Bench v1.0: a family sized like a real ticket

## What this cohort was for

Two cohorts in a row ended with two families that discriminate and a
third that could not. `text-redact` saturated at 39 of 40 with its code
point hazard never firing once, and `redact-spans`, the same contract
with every signpost stripped out and more hidden cases able to catch a
wrong unit, then passed 10 of 10 on a probe. Hiding a hazard inside a
small task does not make the task hard.

So `expr-eval` moves the size instead. Its ticket is eight lines and
points at a `SPEC.md` in the workspace; its reference is a tokenizer, a
precedence climbing parser, and an evaluator. That is the shape the
DeepSWE comparison has pointed at since v0.7: their median instruction
is 15 lines over an 844 line patch, against 69 to 82 lines over about
300 here.

| Family | What it rewards |
|---|---|
| `circuit-breaker` | not dropping a case of a union that crosses files |
| `expr-eval` | what an integer is: 64 bits, two's complement |
| `money-rollup` | exact rational arithmetic in the standard library |

**119 rollouts, $0.849144 measured spend.**

## Results by family

This is the estimand. The pooled table further down is not.

| Family | Spread | Ordering |
|---|---:|---|
| `circuit-breaker` | 6 runs | Go 8/8 > TypeScript 5/8 > JavaScript 4/8 > Python (typed) 4/8 > Python 2/8 |
| `expr-eval` | 7 runs | JavaScript 7/8 > Python 4/8 > Python (typed) 4/8 > TypeScript 3/8 > Go 0/8 |
| `money-rollup` | 1 run | Python (typed) 8/8 > Go 7/8 > JavaScript 7/8 > Python 7/8 > TypeScript 7/7 |

A family counts as discriminating only if its best and worst arms differ
by at least 2 runs out of eight, the same bar v0.9 used. One run
of separation is not an ordering.

## Does any language lead everywhere?

Families that discriminate: `circuit-breaker`, `expr-eval`.
Flat by that test, contributing no correctness signal: `money-rollup`.

No language is top on every family that discriminates. None is bottom on every one either.

Reversals, where one language is best on one family and worst on another:

- Go: best on `circuit-breaker`, worst on `expr-eval`

## What the new family bought

`expr-eval` is the first third family in three cohorts that separates
the arms, and it separates them further than either of the families it
was added to: a spread of 7 runs out of 8, against 6 for
`circuit-breaker`. It also produces the cleanest reversal this repo has
measured. Go passes every `circuit-breaker` rollout and none of the
`expr-eval` ones. Both orderings follow from what the family rewards, so
neither is a fact about Go.

Go's failure is worth stating precisely, because the obvious reading is
wrong. Go is the arm that gets the contract's arithmetic for free:
`int64` wraps, `/` truncates toward zero, `>>` propagates the sign. What
it does not get for free is everything around that, and that is where it
failed: reading a literal as `uint64` before reinterpreting it, checking
a shift count, and spelling bitwise complement `^x` where the contract
writes `~x`. Go rollouts also worked hardest, at 13.25 steps against
8.25 for JavaScript, and still finished at zero. Having the semantics
built into the language did not help; having to say them out loud is a
different skill.

The matched JavaScript and TypeScript pair splits here, 7 of 8 against 3
of 8, and the typed arm is the one that does worse while spending 3.25
more steps. Eight attempts per cell cannot carry that as a finding, and
v0.9 measured a single-seed swing of 4 runs out of 8 on a fixed cell, so
read it as a cell worth more seeds rather than as an effect.

`money-rollup` went flat, at 36 of 39 with a spread of 1 run, after
discriminating in both v0.8 and v0.9. Its instruction changed in this
revision, so there is no honest way to attribute that here, and it is
the reason a family needs re-probing after its text changes rather than
an inherited status.

## Getting the integer width wrong

Seven `expr-eval` hidden cases fail specifically when the width, the
division rule, or the wrap is wrong: `wraparound`,
`hex-and-signed-literals`, `literal-range`, `division-truncation`,
`shift-semantics`, `shift-range`, and `bitwise-full-width`. This is the
mechanism the family was built to expose, and unlike v0.9's code point
hazard it does fire.

| Language | Runs | Runs failing a width case | Rate |
|---|---:|---:|---:|
| JavaScript | 8 | 0 | 0.00 |
| TypeScript | 8 | 2 | 0.25 |
| Python | 8 | 0 | 0.00 |
| Python (typed) | 8 | 0 | 0.00 |
| Go | 8 | 5 | 0.62 |

## Results by family and arm

| Family | Language | Passed | Pass rate | Mean steps |
|---|---|---:|---:|---:|
| `circuit-breaker` | JavaScript | 4/8 | 0.50 | 5.88 |
| `circuit-breaker` | TypeScript | 5/8 | 0.62 | 6.50 |
| `circuit-breaker` | Python | 2/8 | 0.25 | 5.75 |
| `circuit-breaker` | Python (typed) | 4/8 | 0.50 | 6.50 |
| `circuit-breaker` | Go | 8/8 | 1.00 | 7.50 |
| `expr-eval` | JavaScript | 7/8 | 0.88 | 8.25 |
| `expr-eval` | TypeScript | 3/8 | 0.38 | 11.50 |
| `expr-eval` | Python | 4/8 | 0.50 | 7.25 |
| `expr-eval` | Python (typed) | 4/8 | 0.50 | 8.38 |
| `expr-eval` | Go | 0/8 | 0.00 | 13.25 |
| `money-rollup` | JavaScript | 7/8 | 0.88 | 6.88 |
| `money-rollup` | TypeScript | 7/7 | 1.00 | 7.43 |
| `money-rollup` | Python | 7/8 | 0.88 | 6.88 |
| `money-rollup` | Python (typed) | 8/8 | 1.00 | 8.00 |
| `money-rollup` | Go | 7/8 | 0.88 | 8.00 |

## Pooled across all three families

Reported for completeness. Pooling families that disagree produces a
number that describes none of them.

| Language | Passed | Pass rate (95% CI) | Mean steps | Mean cost |
|---|---:|---:|---:|---:|
| Go | 15/24 | 0.62 [0.43, 0.79] | 9.58 | $0.008338 |
| JavaScript | 18/24 | 0.75 [0.55, 0.88] | 7.00 | $0.006531 |
| Python | 13/24 | 0.54 [0.35, 0.72] | 6.62 | $0.006395 |
| Python (typed) | 16/24 | 0.67 [0.47, 0.82] | 7.62 | $0.006987 |
| TypeScript | 15/23 | 0.65 [0.45, 0.81] | 8.52 | $0.007440 |

## Contrasts whose interval excludes zero

- JavaScript passed 0.261 more often than Python (95% CI [0.087, 0.435])
- JavaScript needed 1.57 fewer agent steps than TypeScript (95% CI [-2.565, -0.609])
- JavaScript needed 0.70 fewer agent steps than Python (typed) (95% CI [-1.348, -0.087])
- JavaScript needed 2.74 fewer agent steps than Go (95% CI [-3.696, -1.739])
- TypeScript needed 1.87 more agent steps than Python (95% CI [0.913, 2.957])
- TypeScript needed 1.17 fewer agent steps than Go (95% CI [-1.957, -0.391])
- Python needed 1.00 fewer agent steps than Python (typed) (95% CI [-1.696, -0.348])
- Python needed 3.04 fewer agent steps than Go (95% CI [-4.174, -1.913])
- Python (typed) needed 2.04 fewer agent steps than Go (95% CI [-3.130, -0.957])

## Why there is no drift table

v0.9 carried one, comparing each family against v0.8 with nothing
changed but the seed, and it was the most useful number in that report:
the largest single move was 4 runs out of 8.

This cohort cannot carry one. `money-rollup` and `circuit-breaker` used
to end their instructions by listing the topics their hidden tests
cover, which hands the agent a checklist of what the grader looks at.
That line is gone as of task text revision v1.0, so these two families
ran against different text than they did in v0.8 and v0.9. Their pass
rates here are not comparable with those cohorts, and printing a change
column would invite exactly that comparison.

## Scope and limits

Three brownfield families, five arms, eight attempts per cell, one model
rung, one bash-only scaffold. Three families is still below the point
where between-family variance is well estimated, so this supports claims
about these three tasks and no language-general claim.

The stopping rule was fixed at 120 rollouts before the first paid call
and no interim analysis informed continuation. `expr-eval` reached this
cohort through two pre-registered probes, reported in full in
`docs/EXPR_EVAL_PROBE.md`; those 20 rollouts are not pooled here and the
cohort ran on fresh seeds.

Agent wall time is not reported. This cohort ran four rollouts at a time,
so elapsed time includes contention. All three families are command-mode,
so no timing-sensitive verifier case was exposed to it.

The families were chosen to reward different things, so disagreement
between them is partly by construction. That is the point: it shows the
ordering is a property of the task, not of the language. It does not show
how often real tickets look like any one of these three.
