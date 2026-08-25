# Language AI Bench: interim balanced polyglot report

## Bottom line

**All 20 valid attempts in the balanced four-language brownfield cohort passed.** Correctness tied, while efficiency and workflow measurements still varied.

The full public history now contains 32 valid completions, including the earlier JavaScript/TypeScript greenfield study. The new comparative cohort uses two matched existing-project task families with five runs per language: two optimistic-concurrency attempts and three schedule-data-model attempts.

## Balanced results

| Language | Optimistic concurrency | Schedule variants | Total | Mean cost | Mean output | Mean steps | Mean agent time |
|---|---:|---:|---:|---:|---:|---:|---:|
| JavaScript | 2/2 | 3/3 | 5/5 | $0.005514 | 2302 | 7.00 | 33.66s |
| TypeScript | 2/2 | 3/3 | 5/5 | $0.005496 | 2132 | 6.60 | 49.13s |
| Python | 2/2 | 3/3 | 5/5 | $0.005698 | 2536 | 6.80 | 31.32s |
| Go | 2/2 | 3/3 | 5/5 | $0.006450 | 2695 | 8.20 | 45.96s |

## How the agent got there

| Language | First verifier pass | Mean verifier invocations | Passing verification before submit | Malformed actions |
|---|---:|---:|---:|---:|
| JavaScript | 4/5 | 2.60 | 4/5 | 0 |
| TypeScript | 4/5 | 1.80 | 4/5 | 0 |
| Python | 5/5 | 2.60 | 5/5 | 0 |
| Go | 1/4 | 2.80 | 3/5 | 0 |

These are descriptive estimates from five runs per language, not a general language ranking. Agent steps count model actions; agent time excludes container setup. Explicit verifier counts come from trajectories and do not split out checks performed inside `scripts/verify-local`.

## Infrastructure exclusion and spend

One additional Go trial was excluded before submission because Pier's egress proxy temporarily failed DNS resolution. It consumed $0.00068230; no completed patch was graded. Total measured provider spend, including that excluded event and the earlier study, was **$0.17974737**.

## Scope

The 20-run comparison is balanced retrospectively across languages but was assembled in stages rather than launched as one prospective randomized batch. It still covers only two related backend task families, one model, one effort level, and one bash-only agent scaffold. The earlier 12 JavaScript/TypeScript greenfield runs remain published as a separate extension and are not pooled into the four-language estimator.

See `data/polyglot-results.json` for machine-readable aggregates and `DECISION_REPORT.md` for the earlier report.
