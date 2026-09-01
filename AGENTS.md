# Working notes for agents in this repo

Read `README.md` and `docs/DESIGN.md` first. This file is the shortlist of
things that are easy to get wrong here and expensive to undo.

## Write like an engineer

Plain, short, concrete. Say what the thing does and what it costs. This applies
to the README, the site, reports, commit messages, code comments, and anything
else a human reads.

- No marketing voice. Nothing is "powerful", "seamless", "cutting-edge",
  "robust", "leverages", or "unlocks".
- No theory-speak or invented vocabulary. If a plain word works, use it.
  "Types helped" beats "the type system mediated a corrective feedback loop".
- Name the number. "Python passed 8 of 8, Go 6 of 8" beats "Python performed
  strongly".
- Say the boring truth. "This spans zero, so we cannot tell them apart at this
  sample size" is a finding, and it is how it should be written.
- No em dashes in `README.md` or anything under `docs/`. `scripts/validate-pages.sh`
  rejects them and a failure there silently stops the site updating.
- Avoid internal jargon in reader-facing copy. `validate-pages.sh` already
  rejects the word "arm" in the landing page for this reason.

Commit subjects follow the existing pattern: a lowercase area prefix, a colon,
and a plain statement of what changed. `tasks:`, `calibrate:`, `study:`,
`report:`, `site:`, `runner:`, `docs:`, `fix:`, `analysis:`.

## Never spend before the gate is green

Calibration costs nothing and blocks everything. For any task change:

```sh
python3 scripts/calibrate.py --task-dir tasks/<family> \
  --languages javascript typescript python python-typed go
```

Green means three things at once: the reference passes 100% in every language,
the untouched starter fails the *same case ids* in every language, and every
sabotage is caught by the *same case ids* in every language. Each family keeps
its own receipt in `calibration/`, and study, probe, and schedule JSON lives in
`studies/`.

`python3 scripts/audit_task_integrity.py` is the other free gate. It requires
`src/` and `environment/src/` to be byte-identical, `instruction.md` to be
byte-identical across the five languages of a family, `tests/verify.py` to be
byte-identical to the family's shared `verifier/verify.py`, and source lines to
stay under 140 characters.

## Fix the number of runs before you look at any result

The v0.7 cohort decided to continue after seeing the first batch, and now every
report has to carry that caveat forever. Write `attempts_per_cell` and the
stopping rule into the study JSON, plan the schedule, and then run it. The
`--limit` flag on `scripts/run_pier_schedule.py` is for infrastructure
checkpoints only, never for peeking at pass rates and deciding whether to go on.

## Task design

Each family should discriminate for a *different* reason. The two hard families
disagree with each other, and that disagreement is the most useful result the
repo has produced:

| Family | What it rewards | Who leads |
|---|---|---|
| `money-rollup` | exact arithmetic in the standard library | Python |
| `circuit-breaker` | not dropping a case of a union that crosses files | Go, TypeScript |
| `text-redact` | knowing what a string is at runtime | nobody, it saturated |
| `redact-spans` | the same, with the hazard not announced | nobody, unadmitted |

A new family that repeats an existing mechanism buys almost nothing. Past
roughly five seeds per cell, another family is worth more than more seeds.

**A green gate does not mean the task is hard.** `text-redact` passed
calibration in all five languages, its starter failed ten of twelve checks, and
it still passed 39 of 40 paid attempts with its intended hazard never firing
once. Before a new family joins a cohort, run the ten-rollout difficulty probe:
two attempts in each language at the target rung, admission threshold written
into the probe JSON first, and the family admitted only if it passes at most
seven of ten. That costs about $0.06 and protects a 40-rollout family block. The
gate proves the scoring is fair; only a paid probe tells you the task
discriminates.

**Do not telegraph the hazard in the instruction.** `text-redact` gave its
code point rule a paragraph of its own and added that it does not matter how
your language indexes a string. State the contract once, plainly, and let the
hidden cases do the catching.

**And do not expect that to be enough.** `redact-spans` is `text-redact` with
every signpost removed and three more hidden cases that a wrong unit breaks. It
probed 10 of 10 with zero wrong-unit failures. The hazard was not saturating
because it was advertised; the model is just good at this. When a family
saturates, the lever that is left is size, not subtlety: a DeepSWE reference
patch is 844 lines against 301 here, over an instruction 15 lines long against
69 here.

Copy `tasks/circuit-breaker` as the template. What makes it a good one: a
command-line program reading one JSON document from stdin, everything
time-dependent passed in as data so runs are repeatable, three source files so
types have to cross file boundaries, a long list of bad inputs that must be
rejected, and a starter that fails at least nine of the twelve checks.

Two constraints that are easy to trip over:

- **The starter must fail the same case ids in every language.** If a hidden
  case would pass on the Python starter and fail on the Go one, the gate is red
  and the family is unusable. The fix is to make every hidden case exercise
  something the starter does not have, not to weaken the case.
- **Sabotages must be logic-level.** A sabotage that is a no-op in one language
  cannot be caught by the same case ids everywhere. Anything that depends on a
  language's runtime representation belongs in the task, as a hazard for the
  agent, not in the gate.

## Verification is black box

Observable behavior only: stdin, stdout, exit status. Never require a particular
function or class name, never inspect the AST, never require a specific
algorithm. Line counts are an outcome to measure, never a definition of
equivalence.

## Cost

Every paid run needs a dedicated key with a provider-side hard cap. Measure a
two-rollout pilot, write the measured per-rollout cost into the study JSON, and
let `run_pier_schedule.py` enforce the ceiling. Recent cohorts have run about
$0.006 a rollout, so a 120-rollout matrix is well under a dollar. There is no
excuse for guessing.
