# Language AI Bench v0.7: one hard task, four languages, two model rungs

## Why this study exists

Every earlier cohort saturated. In v0.6 all 36 attempts passed, so the measured correctness difference between languages was exactly zero by construction and no interval could be estimated. A benchmark whose tasks are all solved cannot answer whether the language matters.

v0.7 changes two things. It adds `money-rollup`, a four-file brownfield refactor that replaces floating-point money handling with exact rational arithmetic, adds shortest-path currency conversion with ambiguity rejection, adds ancestor rollups, and adds a large rejection surface. And it runs that one family at more than one model strength, because whether the language matters may itself depend on how capable the agent is.

Across the whole cohort, **84/121 attempts passed**.

## Bottom line

The ceiling is broken. On the `openrouter/openai/gpt-5.6-luna` rung the hard family passed 84/96 rather than everything, so language contrasts are now estimable. Correctness moves: JavaScript passed 0.250 less often than Python (95% CI [0.083, 0.417]); Go passed 0.167 less often than Python (95% CI [0.042, 0.333]). Effort moves further: TypeScript needed 0.67 more agent steps than JavaScript (95% CI [0.12, 1.25]); Go needed 1.50 more agent steps than JavaScript (95% CI [0.83, 2.21]); TypeScript needed 0.71 more agent steps than Python (95% CI [0.25, 1.21]); Go needed 0.83 more agent steps than TypeScript (95% CI [0.04, 1.67]); Go needed 1.54 more agent steps than Python (95% CI [0.75, 2.38]). On the weaker `openrouter/openai/gpt-5-mini` rung the same task is a cliff: 0/25 passed in every language, so no language rescues a weaker agent.

## Results by model rung

### Strong rung: `openrouter/openai/gpt-5.6-luna`

84/96 passed overall (0.88, 95% CI [0.79, 0.93]).

| Language | Passed | Pass rate (95% CI) | Mean steps | Mean output tokens | Mean agent time | Mean cost |
|---|---:|---:|---:|---:|---:|---:|
| JavaScript | 18/24 | 0.75 [0.55, 0.88] | 6.50 | 3124 | 37.1s | $0.005668 |
| TypeScript | 22/24 | 0.92 [0.74, 0.98] | 7.17 | 3201 | 50.5s | $0.006356 |
| Python | 24/24 | 1.00 [0.86, 1.00] | 6.46 | 2925 | 36.4s | $0.005462 |
| Go | 20/24 | 0.83 [0.64, 0.93] | 8.00 | 3750 | 49.5s | $0.007030 |

Paired differences within matched attempt blocks, with 95% percentile intervals from a fixed-seed 20,000-resample paired bootstrap:

| Contrast | Pass-rate difference (95% CI) | Agent-step difference (95% CI) |
|---|---:|---:|
| JavaScript minus TypeScript | -0.167 [-0.375, 0.000] | -0.67 [-1.25, -0.12] |
| JavaScript minus Python | -0.250 [-0.417, -0.083] | 0.04 [-0.46, 0.58] |
| JavaScript minus Go | -0.083 [-0.333, 0.167] | -1.50 [-2.21, -0.83] |
| TypeScript minus Python | -0.083 [-0.208, 0.000] | 0.71 [0.25, 1.21] |
| TypeScript minus Go | 0.083 [-0.125, 0.292] | -0.83 [-1.67, -0.04] |
| Python minus Go | 0.167 [0.042, 0.333] | -1.54 [-2.38, -0.75] |

Failing verifier cases, counted across all runs of that language:

| Language | Failing cases |
|---|---|
| JavaScript | rejects-invalid x4, half-even-ties x3, zero-and-negative-formatting x3, chained-conversion x1, shortest-path-preferred x1, per-entry-rounding x1, exact-large-magnitude x1 |
| TypeScript | rejects-invalid x1, shortest-path-preferred x1 |
| Python | none |
| Go | rejects-invalid x3, half-even-ties x1, zero-and-negative-formatting x1 |

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
| JavaScript | 18/30 | 0.60 [0.42, 0.75] | 8.53 | $0.007218 |
| TypeScript | 22/30 | 0.73 [0.56, 0.86] | 9.73 | $0.009090 |
| Python | 24/31 | 0.77 [0.60, 0.89] | 9.19 | $0.009137 |
| Go | 20/30 | 0.67 [0.49, 0.81] | 9.03 | $0.007714 |

Pooling mixes model rungs and is descriptive only; the rung tables above are the estimates to read.

## Scope

One hard brownfield family, four languages, 2 model rungs, one low-effort bash-only scaffold (mini-swe-agent@2.4.6). Measured provider spend for this cohort was **$1.00391751**.

Topology is part of the treatment bundle: starter file counts, toolchains, and ecosystems differ by language, so any difference must not be read as a syntax-only effect. Task difficulty is part of the bundle too: this is one family, and a different hard task could rank languages differently.

## How the cohort was collected

The strong rung was collected in 2 batches of equal size. The first batch was planned and run before any result was seen. The decision to run the second was made after reading the first, specifically because the Python versus Go pass-rate interval touched zero, so the continuation was outcome-dependent even though the batch size was fixed in advance and no batch was stopped early on a result. Readers who want a contrast free of that dependency should treat the second batch alone as the confirmatory sample. Attempt blocks are namespaced per batch, so pairing never mixes attempts across batches.
