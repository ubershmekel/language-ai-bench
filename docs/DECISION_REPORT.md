# Language AI Bench: first cross-language report

## Bottom line

**All 24 published attempts passed. Correctness tied; workflow efficiency remains measurable.**

The balanced primary study contains 22 JavaScript/TypeScript attempts across new and existing Node projects. Python and Go each add one illustrative run of the existing optimistic-concurrency task. Those two 1/1 results prove that the calibrated four-language pipeline works end to end; they do not estimate Python or Go success rates and should not be compared as if they were equally sampled benchmark cells.

## What the benchmark asked

The first task requires an agent to add optimistic concurrency to a task service: stable ETags, required If-Match headers, stale-write rejection, correct deletion behavior, and protection against two conflicting writes both succeeding. The existing-project condition starts from working CRUD code. The new-project condition starts from a minimal Node scaffold.

One fresh mini-swe-agent context receives one repository and the behavior-focused prompt. A shared language-neutral HTTP verifier grades the final service. A pass means the complete hidden behavior contract succeeded; 6/6 means six independent agent attempts passed, not six test cases.

## Balanced JavaScript/TypeScript study

| Condition | Language | Passed | Pass rate | Mean cost | Mean output | Mean steps | Mean agent time |
|---|---|---:|---:|---:|---:|---:|---:|
| Brownfield | JavaScript | 5/5 | 100% | $0.005514 | 2302 | 7.00 | 33.66s |
| Brownfield | TypeScript | 5/5 | 100% | $0.005496 | 2132 | 6.60 | 49.13s |
| Greenfield | JavaScript | 6/6 | 100% | $0.005335 | 2543 | 6.50 | 35.81s |
| Greenfield | TypeScript | 6/6 | 100% | $0.005211 | 2430 | 5.83 | 45.13s |

Descriptive TypeScript-versus-JavaScript differences:

- **Brownfield:** pass-rate difference 0 points; output tokens -7.39%, steps -5.71%, cost -0.32%, agent time +45.96%.
- **Greenfield:** pass-rate difference 0 points; output tokens -4.46%, steps -10.31%, cost -2.32%, agent time +26.03%.

Every balanced cell reached 100%, so the observed accuracy difference is zero. The recorded token, step, and wall-time values are retained for auditability, but this cohort predates source-integrity checks and used inconsistently formatted fixtures. Treat those efficiency contrasts as confounded historical telemetry, not language effects.

## Workflow quality among the 22 balanced runs

| Language | First verifier pass | Mean verifier invocations | Passing verification before submit | Malformed actions |
|---|---:|---:|---:|---:|
| JavaScript | 8/11 | 2.45 | 10/11 | 0 |
| TypeScript | 7/11 | 2.09 | 9/11 | 0 |

These trajectory-derived measures compare how the agent reached a correct result. They count explicit `scripts/verify-local` commands; checks performed inside that script are not separately visible. Patch-size and review metrics are unavailable because these Pier jobs did not retain final workspaces.

## Python and Go examples

| Language | Type feedback | Condition | Passed | Cost | Output | Steps | Agent time |
|---|---|---|---:|---:|---:|---:|---:|
| Python | none | Existing | 1/1 | $0.006897 | 3257 | 9 | 40.29s |
| Go | compiler | Existing | 1/1 | $0.005861 | 2952 | 6 | 40.53s |

Both examples passed the same hidden optimistic-concurrency verifier with no exceptions. Because each language has only one paid attempt, the result licenses only an end-to-end pipeline claim: this agent solved this instance once in Python and once in Go.

## What the results support

- The tested agent completed the optimistic-concurrency task at least once in all four language arms.
- JavaScript and strict TypeScript completed every balanced new- and existing-project attempt.
- Strict TypeScript imposed no observed completion penalty in the balanced study.

## What the results do not support

The report is not a four-language ranking. Python and Go have different ecosystems, compiler behavior, diagnostics, and likely model exposure, and each has only one agent attempt. The study also uses one model snapshot, low reasoning effort, a bash-only scaffold, related backend contracts, and no editor/LSP feedback. It does not measure long-term maintenance, frontend work, dependency migrations, human review, or future defect rates.

Total measured spend across all 24 published attempts was **$0.13108191**. Raw Pier jobs remain private; the public JSON contains aggregates only.

See data/decision-results.json for machine-readable aggregates and confidence intervals.
