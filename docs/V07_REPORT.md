# Language AI Bench v0.7: one hard task, four languages, two model rungs

## Why this study exists

Every earlier cohort saturated. In v0.6 all 36 attempts passed, so the measured correctness difference between languages was exactly zero by construction and no interval could be estimated. A benchmark whose tasks are all solved cannot answer whether the language matters.

v0.7 changes two things. It adds `money-rollup`, a four-file brownfield refactor that replaces floating-point money handling with exact rational arithmetic, adds shortest-path currency conversion with ambiguity rejection, adds ancestor rollups, and adds a large rejection surface. And it runs that one family at more than one model strength, because whether the language matters may itself depend on how capable the agent is.

Across the whole cohort, **42/73 attempts passed**.

## Bottom line

The ceiling is broken. On the `openrouter/openai/gpt-5.6-luna` rung the hard family passed 42/48 rather than everything, so language contrasts are now estimable. Correctness still barely moves: no pass-rate contrast has an interval excluding zero. Effort does move: Go needed 1.33 more agent steps than JavaScript (95% CI [-2.25, -0.42]); Go needed 1.33 more agent steps than TypeScript (95% CI [-2.42, -0.42]); Go needed 1.67 more agent steps than Python (95% CI [-2.92, -0.50]). On the weaker `openrouter/openai/gpt-5-mini` rung the same task is a cliff: 0/25 passed in every language, so no language rescues a weaker agent.

## Results by model rung

### Strong rung: `openrouter/openai/gpt-5.6-luna`

42/48 passed overall (0.88, 95% CI [0.75, 0.94]).

| Language | Passed | Pass rate (95% CI) | Mean steps | Mean output tokens | Mean agent time | Mean cost |
|---|---:|---:|---:|---:|---:|---:|
| JavaScript | 10/12 | 0.83 [0.55, 0.95] | 6.92 | 3202 | 38.2s | $0.005879 |
| TypeScript | 11/12 | 0.92 [0.65, 0.99] | 6.92 | 3109 | 48.6s | $0.006125 |
| Python | 12/12 | 1.00 [0.76, 1.00] | 6.58 | 2969 | 37.2s | $0.005520 |
| Go | 9/12 | 0.75 [0.47, 0.91] | 8.25 | 3710 | 48.5s | $0.006978 |

Paired differences within matched attempt blocks, with 95% percentile intervals from a fixed-seed 20,000-resample paired bootstrap:

| Contrast | Pass-rate difference (95% CI) | Agent-step difference (95% CI) |
|---|---:|---:|
| JavaScript minus TypeScript | -0.083 [-0.333, 0.167] | 0.00 [-0.58, 0.67] |
| JavaScript minus Python | -0.167 [-0.417, 0.000] | 0.33 [-0.58, 1.25] |
| JavaScript minus Go | 0.083 [-0.250, 0.417] | -1.33 [-2.25, -0.42] |
| TypeScript minus Python | -0.083 [-0.250, 0.000] | 0.33 [-0.33, 1.00] |
| TypeScript minus Go | 0.167 [-0.167, 0.500] | -1.33 [-2.42, -0.42] |
| Python minus Go | 0.250 [0.000, 0.500] | -1.67 [-2.92, -0.50] |

Failing verifier cases, counted across all runs of that language:

| Language | Failing cases |
|---|---|
| JavaScript | rejects-invalid x1, half-even-ties x1, zero-and-negative-formatting x1 |
| TypeScript | rejects-invalid x1 |
| Python | none |
| Go | rejects-invalid x2, half-even-ties x1, zero-and-negative-formatting x1 |

### Mid rung: `openrouter/openai/gpt-5-mini`

0/25 passed overall (0.00, 95% CI [0.00, 0.13]).

| Language | Passed | Pass rate (95% CI) | Mean steps | Mean output tokens | Mean agent time | Mean cost |
|---|---:|---:|---:|---:|---:|---:|
| JavaScript | 0/6 | 0.00 [0.00, 0.39] | 16.67 | 3833 | 64.2s | $0.013421 |
| TypeScript | 0/6 | 0.00 [0.00, 0.39] | 20.00 | 5352 | 95.2s | $0.020026 |
| Python | 0/7 | 0.00 [0.00, 0.35] | 18.57 | 6312 | 99.2s | $0.021736 |
| Go | 0/6 | 0.00 [0.00, 0.39] | 13.17 | 2681 | 51.2s | $0.010450 |

Paired differences within matched attempt blocks, with 95% percentile intervals from a fixed-seed 20,000-resample paired bootstrap:

| Contrast | Pass-rate difference (95% CI) | Agent-step difference (95% CI) |
|---|---:|---:|
| JavaScript minus TypeScript | 0.000 [0.000, 0.000] | -3.33 [-12.67, 6.00] |
| JavaScript minus Python | 0.000 [0.000, 0.000] | -2.17 [-10.67, 7.17] |
| JavaScript minus Go | 0.000 [0.000, 0.000] | 3.50 [-2.17, 9.67] |
| TypeScript minus Python | 0.000 [0.000, 0.000] | 1.17 [-4.00, 5.67] |
| TypeScript minus Go | 0.000 [0.000, 0.000] | 6.83 [-0.67, 14.50] |
| Python minus Go | 0.000 [0.000, 0.000] | 5.67 [0.00, 10.67] |

Failing verifier cases, counted across all runs of that language:

| Language | Failing cases |
|---|---|
| JavaScript | rejects-invalid x6, chained-conversion x4, half-even-ties x4, exact-large-magnitude x4, shortest-path-preferred x1, rejects-bad-paths x1, ancestor-rollup x1, per-entry-rounding x1, zero-and-negative-formatting x1, prefix-sorting x1 |
| TypeScript | half-even-ties x6, rejects-invalid x6, chained-conversion x4, exact-large-magnitude x4, shortest-path-preferred x1, regression-flat-accounts x1, ancestor-rollup x1, per-entry-rounding x1, zero-and-negative-formatting x1, prefix-sorting x1 |
| Python | rejects-invalid x7, chained-conversion x2, half-even-ties x2, exact-large-magnitude x2, shortest-path-preferred x1, per-entry-rounding x1, zero-and-negative-formatting x1 |
| Go | chained-conversion x6, half-even-ties x6, exact-large-magnitude x6, rejects-invalid x6 |

## Pooled across rungs

| Language | Passed | Pass rate (95% CI) | Mean steps | Mean cost |
|---|---:|---:|---:|---:|
| JavaScript | 10/18 | 0.56 [0.34, 0.75] | 10.17 | $0.008393 |
| TypeScript | 11/18 | 0.61 [0.39, 0.80] | 11.28 | $0.010758 |
| Python | 12/19 | 0.63 [0.41, 0.81] | 11.00 | $0.011494 |
| Go | 9/18 | 0.50 [0.29, 0.71] | 9.89 | $0.008135 |

Pooling mixes model rungs and is descriptive only; the rung tables above are the estimates to read.

## Scope

One hard brownfield family, four languages, 2 model rungs, one low-effort bash-only scaffold (mini-swe-agent@2.4.6). Measured provider spend for this cohort was **$0.70954969**.

Topology is part of the treatment bundle: starter file counts, toolchains, and ecosystems differ by language, so any difference must not be read as a syntax-only effect. Task difficulty is part of the bundle too: this is one family, and a different hard task could rank languages differently.
