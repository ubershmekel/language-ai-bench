# expr-eval difficulty probes

Ten rollouts each, two per language, at the same rung the cohorts use.
These are go/no-go decisions on the task. They estimate no pass rate and
must never be pooled with a cohort result.

## The pre-registered rule

Admit only if the family passes at most 7 of 10 and at least 1 of 10.
The upper bound catches saturation, which is how `text-redact` and
`redact-spans` failed. The lower bound catches a wall: a family every
arm fails ranks nothing either.

## First probe: 15 cases, two developer cases

**0 of 10 passed. 6 of 10 failed at least one integer-width case. $0.090087 measured spend.**

Verdict against the pre-registered rule: **do not admit**.

| Language | Passed | Failed a width case | Median cases failed | Median steps |
|---|---:|---:|---:|---:|
| JavaScript | 0/2 | 1 | 4 | 7 |
| TypeScript | 0/2 | 2 | 5 | 13 |
| Python | 0/2 | 0 | 2 | 6 |
| Python (typed) | 0/2 | 2 | 4 | 7 |
| Go | 0/2 | 1 | 6 | 14 |

Cases by how many rollouts failed them:

| Case | Rollouts |
|---|---:|
| `parse-errors` | 8/10 |
| `undefined-name` | 5/10 |
| `wraparound` | 4/10 |
| `division-truncation` | 3/10 |
| `precedence-table` | 2/10 |
| `shift-range` | 2/10 |
| `hex-and-signed-literals` | 2/10 |
| `literal-range` | 2/10 |
| `depth-limit` | 2/10 |
| `rejects-invalid` | 1/10 |
| `bitwise-full-width` | 1/10 |

## Second probe: 20 cases, seven developer cases

**4 of 10 passed. 4 of 10 failed at least one integer-width case. $0.096555 measured spend.**

Verdict against the pre-registered rule: **admit**.

| Language | Passed | Failed a width case | Median cases failed | Median steps |
|---|---:|---:|---:|---:|
| JavaScript | 1/2 | 0 | 2 | 12 |
| TypeScript | 1/2 | 1 | 1 | 9 |
| Python | 2/2 | 0 | 0 | 7 |
| Python (typed) | 0/2 | 1 | 2 | 14 |
| Go | 0/2 | 2 | 17 | 12 |

Cases by how many rollouts failed them:

| Case | Rollouts |
|---|---:|
| `precedence-table` | 4/10 |
| `division-truncation` | 3/10 |
| `undefined-name` | 3/10 |
| `precedence-basics` | 2/10 |
| `errors-basics` | 2/10 |
| `bindings-basics` | 2/10 |
| `shift-semantics` | 2/10 |
| `shift-range` | 2/10 |
| `bindings-and-shadowing` | 2/10 |
| `parse-errors` | 2/10 |
| `bitwise-full-width` | 2/10 |
| `literal-range` | 1/10 |
| `regression-sum` | 1/10 |
| `wraparound-basics` | 1/10 |
| `division-signs` | 1/10 |
| `wraparound` | 1/10 |
| `hex-and-signed-literals` | 1/10 |
| `depth-limit` | 1/10 |

## What the two probes together say

The first probe is the useful one. Zero passes, but no rollout ran out
of steps or context, every rollout wrote a working interpreter in 5 to
14 steps, and each failed only 1 to 6 of the 15 cases with a different
set each time. A task can be far too hard to score while being nowhere
near too hard to do, and what made it unscoreable was the number of
independent requirements, not the difficulty of any one of them.

The second probe changed the feedback available rather than the work.
Five developer cases now cover the shapes the first probe kept missing;
the corners stay hidden. That moved 0 of 10 to 4 of 10, which is the
band the design targets, and the failures that remain are real. Two Go
rollouts produced programs that compiled, ran, and were wrong, one of
them panicking on a bad type assertion over an error value.

Two probes of one family is a step worth naming, because it can look
like fitting a task to a target. The line is this: the admission rule
and the rollout count were fixed before each probe and neither changed
after seeing results, both probes are reported, and the family enters a
cohort on fresh seeds. Calibrating a task into the measurable band
before it is used is what the selection ladder already asks for.
Probing variations until a result looks good is not, and a third probe
was ruled out in writing before the second one ran.

