# Language AI Bench v1.0

## What this measures

One model, one agent, one scaffold, fresh context every run. Three
refactors, each authored idiomatically in five setups, each verified by
one language-neutral driver. The only thing that varies within a task is
the language and the type checking that comes with it.

Each task deliberately rewards a different thing, because a type system
is not one lever. It reports the branch you forgot; it says nothing
about whether you rounded correctly.

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
by at least 2 runs out of eight. One run of separation is not an
ordering, and treating it as one manufactures reversals out of noise.

## The task picks the winner

Different tasks ranking the languages differently is the expected
result, not a defect in the measurement. Each of these tasks was built
to stress a different part of writing code, and the languages differ in
which of those parts they help with. An average over them would describe
none of them, which is why every number here is reported per task.

Families that discriminate: `circuit-breaker`, `expr-eval`.
Flat by that test, contributing no correctness signal: `money-rollup`.

No language is top on every family that discriminates. None is bottom on every one either.

Reversals, where one language is best on one family and worst on another:

- Go: best on `circuit-breaker`, worst on `expr-eval`

## Why the tasks rank the languages differently

The three tasks fail for different reasons, and a checker only helps
with one of them.

**`circuit-breaker` rewards being told what you missed.** The work is a
three-state machine and a three-variant outcome union consumed across
file boundaries. Drop a case and the program keeps running and returns
the wrong answer, in JavaScript and in Python. `go build`, `tsc` and
`mypy` all name the missing case at the point of the mistake. Go passes
8 of 8 here; Python, which reports nothing, passes 2 of 8.

**`money-rollup` rewards a library, and a checker is silent about it.**
The failures are rounding mode, negative zero formatting, and the
shortest conversion path. Every one of those type checks cleanly while
being wrong: `half-up` and `half-even` have the same type. What helps is
having exact rational arithmetic in the standard library, which Python
does. This task is flat this cohort, at 36 of 39, so it separates
nothing here, but that is what it separates on when it does.

**`expr-eval` rewards saying the semantics out loud.** The contract is
signed 64-bit two's complement. JavaScript has no such type at all, so
the model has to make a visible decision, reach for `BigInt`, and mask
to 64 bits; it passes 7 of 8. Go already has the semantics in `int64`,
which turns out to be the trap: the parts that are not free, reading a
literal as `uint64` before reinterpreting it, checking a shift count,
and spelling complement `^x` where the contract writes `~x`, get missed.
Go passes 0 of 8 while spending the most steps of any arm.

So a type system helps when the error class is a shape the checker can
see, and does nothing when the error class is a value or a convention.
Both kinds of bug are ordinary. Which one a ticket contains is not a
property of the language you write it in.

## Two results to read carefully

The matched JavaScript and TypeScript pair splits on `expr-eval`, 7 of 8
against 3 of 8, with the typed arm behind while spending 3.25 more
steps. That pair is the analytical centerpiece of this design, so it is
tempting to read. Eight attempts per cell cannot carry it: a rerun of a
fixed cell with nothing changed but the random seed has moved by 4 runs
out of 8 in this project before. Treat it as a cell that needs more
seeds, not as an effect.

`money-rollup` is flat here, at 36 of 39 with a spread of 1 run. Its
instruction was revised for this cohort, so there is no honest way to
separate the text from the seed, and the family is marked for re-probing
rather than carrying a status it did not earn under the text it ran.

## Getting the integer width wrong

Seven `expr-eval` hidden cases fail specifically when the width, the
division rule, or the wrap is wrong: `wraparound`,
`hex-and-signed-literals`, `literal-range`, `division-truncation`,
`shift-semantics`, `shift-range`, and `bitwise-full-width`. This is the
mechanism the family was built to expose, and it fires.

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

## What each language cost

Cost is measured from the provider's own usage metadata, not estimated.
It tracks agent steps closely, because steps are what buy tokens.

Mean cost per rollout:

```
Go             $0.008338  ████████████████████████████
TypeScript     $0.007440  █████████████████████████
Python (typed) $0.006987  ███████████████████████
JavaScript     $0.006531  ██████████████████████
Python         $0.006395  █████████████████████
```

| Language | Mean cost | Total | Mean steps | Mean output tokens |
|---|---:|---:|---:|---:|
| Go | $0.008338 | $0.2001 | 9.58 | 3,961 |
| TypeScript | $0.007440 | $0.1711 | 8.52 | 3,386 |
| Python (typed) | $0.006987 | $0.1677 | 7.62 | 3,310 |
| JavaScript | $0.006531 | $0.1567 | 7.00 | 3,196 |
| Python | $0.006395 | $0.1535 | 6.62 | 3,071 |

Total spend by task family:

```
expr-eval          $0.3703  ████████████████████████████
money-rollup       $0.2509  ███████████████████
circuit-breaker    $0.2280  █████████████████
```

The whole cohort cost $0.849144. The most expensive
language to run was Go at $0.008338 a rollout, 1.30 times the cheapest, Python.

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

## Why earlier cohorts are not tabulated next to this one

`money-rollup` and `circuit-breaker` used to end their instructions by
listing the topics their hidden tests cover, which hands the agent a
checklist of what the grader looks at. That line is gone, so these two
tasks ran against different text than in any earlier report and their
pass rates are not comparable with those. Printing a change column would
invite exactly that comparison, so there is none.

## Scope and limits

Three brownfield families, five arms, eight attempts per cell, one model
rung, one bash-only scaffold. Three families is below the point where
between-family variance is well estimated, so this supports claims
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
