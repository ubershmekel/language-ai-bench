# Task families: status and evidence

One row per family, with the reason it is in the tree and the measurement that
put it there. A family is only worth its 40 rollouts in a cohort if it can
separate the arms; the rest are kept for reproducibility, not for running.

| Family | Affordance it turns on | Status | Evidence |
|---|---|---|---|
| `circuit-breaker` | not dropping a case of a union that crosses files | active | v0.8 and v0.9 both discriminated; 18 of 40 in v0.9, spread 4 runs |
| `money-rollup` | exact arithmetic in the standard library | active | v0.8 and v0.9 both discriminated; 28 of 40 in v0.9, spread 3 runs |
| `expr-eval` | what an integer is: 64-bit two's complement | active | admitted at 4 of 10 on the second probe, after 0 of 10 on the first |
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
