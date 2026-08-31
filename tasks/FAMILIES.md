# Task families: status and evidence

One row per family, with the reason it is in the tree and the measurement that
put it there. A family is only worth its 40 rollouts in a cohort if it can
separate the arms; the rest are kept for reproducibility, not for running.

| Family | Affordance it turns on | Status | Evidence |
|---|---|---|---|
| `circuit-breaker` | not dropping a case of a union that crosses files | active | discriminated in v0.8, v0.9 and v1.0; spread 6 runs in v1.0, Go 8/8 to Python 2/8 |
| `money-rollup` | exact arithmetic in the standard library | re-probe before reuse | discriminated in v0.8 and v0.9, flat in v1.0 at 36 of 39, spread 1 run, after its instruction changed |
| `expr-eval` | what an integer is: 64-bit two's complement | active | admitted at 4 of 10; discriminated in v1.0 with spread 7 runs, JavaScript 7/8 to Go 0/8 |
| `text-redact` | what a string is at runtime | frozen | saturated in v0.9 at 39 of 40, hazard never fired |
| `redact-spans` | the same, with the hazard not announced | unadmitted | probed 10 of 10 with zero wrong-unit failures |
| `configuration-merge` | data shape and precedence edge cases | retired | 100 percent in v0.6 and again in v0.8 |
| `optimistic-concurrency` | ETag and If-Match state transitions | retired | HTTP era, superseded by the command-mode families |
| `task-service-greenfield` | the same contract built from scratch | retired | HTTP era, greenfield contrast only |
| `schedule-variants` | brownfield and greenfield schedules | retired | HTTP era |

**Retired means do not run, not delete.** Every published cohort pins a repo
revision, so deleting a family would break the reproducibility of the report
that used it. Retired families cost nothing to keep and their numbers are what
justifies retiring them.

**Re-probe before reuse means the family's status did not survive its own text
change.** `money-rollup` discriminated twice and then went flat in the cohort
that first ran it without its hidden-test checklist. Whether that is the text or
the seed is not answerable from one cohort, and a family whose instruction bytes
changed has to earn its status again rather than inherit it.

**Frozen means do not edit.** `text-redact` carries a published headline result.
Its successor is a separate family with a separate id.

## Task text revision v1.0

Three instructions used to end by listing the topics their hidden tests cover:
`money-rollup`, `circuit-breaker`, and `configuration-merge`. That is a
checklist of exactly what the grader looks at, handed to the agent, and it has
been removed. `text-redact` keeps its version of that line because it is frozen.

Cohorts v0.6 through v0.9 ran against the older text. Family results are
comparable only within a repo revision, and every schedule receipt records the
revision it ran at. Do not read a v0.9 pass rate against a later one for the
same family without checking that the instruction bytes are the same.
