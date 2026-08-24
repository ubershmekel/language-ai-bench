# Prompt: Does Language Choice Affect Coding-Agent Success? (Design + Prototype)

You are an expert in AI-agent benchmarking, software-engineering evaluation,
programming-language ergonomics, and experimental design.

## Objective

Design **and implement a minimal, cheap, end-to-end prototype** of an experiment
measuring:

> **How does programming-language choice — and especially the feedback provided
> by its type system and standard tooling — affect the ability of an autonomous
> coding agent to complete the same software-engineering task?**

Target languages: **JavaScript**, **TypeScript**, **Python**, **Go**.

Do not assume stronger typing helps. "Typing hurts" and "no effect detectable at
this sample size" are fully acceptable findings, and the design must be capable
of producing them.

The output is an **MIT-licensed public artifact**. Others must be able to clone
it and run the same experiment against their own model with one command. That
constraint shapes every design decision below.

---

## 0. Read This First: Framing Decisions

### 0.1 The four languages are not four equal arms

- **JS ↔ TS is a matched pair and the analytical centerpiece.** Same runtime,
  package manager, test runner, ecosystem idioms, and error-message conventions.
  The type layer is close to the _only_ varying factor — the cleanest natural
  experiment available for this question. Derive the JS variant from the TS
  variant by type erasure plus idiomatic cleanup, and commit the diff.
- **Python and Go are independent variants** that widen external validity
  (gradual/optional typing; nominal typing with a blocking compiler) but carry
  confounds: different ecosystems, different diagnostic quality, different
  pretraining mass, different test-loop latency.

Report the JS↔TS contrast as high-internal-validity, and the Python/Go contrasts
with confounds named. Never collapse all four into a leaderboard.

**v1 ships exactly four arms — one canonical configuration per language, no
strictness variants:**

| Arm        | `typecheck_config`             | Type feedback        |
| ---------- | ------------------------------ | -------------------- |
| JavaScript | `none` (no `checkJs`)          | none                 |
| Python     | `none` (no checker configured) | none                 |
| TypeScript | `strict` (`strict: true`)      | structural, thorough |
| Go         | `default` (compiler only)      | nominal, blocking    |

That is 4 cells, not 7. Do not add strictness variants in v1.

`typecheck_config` must nevertheless be a **first-class run variable** in the
schema from day one, carrying an explicit value in every record even though v1
uses only one value per language. Adding arms later must not require a schema
migration or invalidate v1 results.

**Be explicit about what this simplification costs.** The within-language
strictness ladder (see §10) was the defense against the Go confound: with only
one configuration per language, a Go–JS difference cannot be attributed to
_typing_ rather than to compilation, ecosystem, diagnostic quality, or
pretraining mass. v1 therefore supports the JS↔TS contrast with reasonable
internal validity and the Python/Go contrasts only descriptively. State this
limitation in the README in those terms rather than implying a four-way ranking
is interpretable.

### 0.2 Build on existing infrastructure; do not write a harness

Datacurve's DeepSWE already establishes the pattern, and its tooling is directly
reusable.

**Adopt the Harbor task format** used by DeepSWE:

```
task.toml        # metadata: repo, base commit, language, image, resource limits
instruction.md   # the prompt the agent sees
environment/     # Dockerfile reproducing the image
tests/           # verifier entry point + held-out tests + grader config
solution/        # reference solution, held out from the agent
```

**Use Pier** (Harbor-compatible, sandboxed, per-agent network allowlists,
trajectory metadata and viewer) as the runner, and **mini-swe-agent** as the
agent.

mini-swe-agent is not merely convenient — it is close to the _correct_ agent for
this specific experiment:

- **Bash-only, no tool-calling interface.** Zero language-specific behavior
  baked into the scaffold. Any agent with structured edit tools, retrieval, or
  LSP would layer language-specific affordances directly on top of the
  independent variable.
- **Completely linear history** — the trajectory _is_ the message list.
  Feedback-to-fix events (§4) become trivially extractable rather than
  reconstructed.
- **Model-agnostic** — anyone can rerun the MIT-licensed artifact against their
  own model without touching the agent.

**One catch to design around:** mini-swe-agent executes each action with an
independent `subprocess.run`, with no persistent shell session. Starting a
long-running dev server is therefore awkward, and — critically — the awkwardness
is _differentially_ distributed across languages (`go build && ./server &` is a
different experience from `npm run dev &`). This asymmetry would land directly
on the dependent variable. Mitigate by shipping an identical-in-spirit
`scripts/verify-local` in every variant that starts, readiness-probes, tests,
and tears down in a single command; or prefer a CLI-contract task over an HTTP
one. State which you chose and why.

**Explicitly do not build:** a harness, a sandbox layer, a trajectory viewer, an
agent framework, a results database, a web UI, a plugin system, or a generalized
benchmarking platform. If a needed capability exists in Pier or mini-swe-agent,
use it and note the dependency. Net new code should be: four repo variants, one
shared verifier, a calibration script, an analysis script, and docs.

### 0.2a The scaffold is a treatment, not a neutral container — say so out loud

The bash-only choice above is the single most contestable decision in this
design, and the design document must confront it directly rather than presenting
mini-swe-agent as an obvious default. Separate two distinct concerns:

**The action interface** (typing bash in a text response vs. calling a
structured `edit_file` tool) is primarily a reliability question. It affects
malformed-action rates and editing ergonomics. It is not on the causal path of
the research question.

**The feedback channel** _is_ on the causal path, and this is the real threat.
If the practical benefit of a type system comes largely through inline editor
feedback — diagnostics at the moment of writing, hover types, go-to-definition —
then a bash-only agent sees type information only when it _chooses_ to run `tsc`
or `go build` and read the output. The experiment would then be measuring "does
the agent decide to invoke the type checker," not "does type information help."
A null result could arise for entirely the wrong reason.

Two things partially defend the choice, and both belong in the write-up:

- **CLI invocation is how most production coding agents actually obtain type
  feedback today.** Claude Code, Codex, and similar tools predominantly run type
  checkers and compilers in a shell and read stderr; their structured tools are
  overwhelmingly file read/write rather than type-information tools. LSP
  integration exists but is not the default path. Bash-only is therefore closer
  to current practice on the _diagnostic_ axis than it first appears — it is the
  _editing_ experience that is less representative.
- **Any richer scaffold bakes language-specific quality into the apparatus.** A
  structured edit tool may handle Python indentation better than Go braces;
  retrieval may index some languages better than others; an LSP hands TS and Go
  far richer information than JS and Python — which _is_ the treatment,
  implemented by a third party with unknown and unmeasured per-language
  fidelity. Running the experiment on a full-featured agent measures _that
  agent's per-language tool quality × language_, with no way to separate the
  terms.

**Resolution: make the scaffold an explicit configuration, not a hidden
assumption.** Pier drives claude-code, codex, gemini-cli, and opencode directly
alongside mini-swe-agent, so a second arm over the same four task variants is
cheap to add.

| Arm                                             | Claim it licenses                                                        |
| ----------------------------------------------- | ------------------------------------------------------------------------ |
| Bash-only (mini-swe-agent)                      | "Holding the agent neutral, language X differs from Y by Z."             |
| Real-agent (e.g. claude-code or codex via Pier) | "Under a scaffold people actually use, the effect does / does not hold." |

Agreement across arms is a robust finding. **Disagreement is the more
interesting result** — it would mean the scaffold _mediates_ the language
effect, which is directly actionable for anyone choosing tooling. Record
`scaffold` as a first-class run variable alongside `model` and
`typecheck_config`. v1 may ship the bash-only arm only, but the schema, layout,
and README must treat it as one arm of a planned two-arm design rather than the
design.

Note that Datacurve names this exact constraint as a DeepSWE limitation — a
fixed mini-swe-agent harness rather than native Claude Code / Codex CLI / Cursor
workflows. Cite it as a known, acknowledged limitation of the approach, not
something the design argues away.

### 0.3 What this contributes over DeepSWE

DeepSWE spans TypeScript, Go, Python, JavaScript, and Rust, but its tasks come
from _different real repositories per language_. Language is therefore fully
confounded with repo, domain, and task difficulty — no language effect is
readable from its leaderboard. **The matched task family is the contribution.**
Say so explicitly in the README, or the obvious reaction is "DeepSWE already
does this."

**Free pilot before building anything:** DeepSWE publishes the rollouts behind
its published numbers. Check whether a per-language signal appears in that
existing corpus. It will be confounded and non-conclusive, but a completely flat
signal is useful information about the effect size you're hunting and costs
nothing.

---

## 1. Model Policy and Cost Discipline

### 1.1 One model for v1

Fix a single model for the first experiment. The model is a **constant under
test-holding**, not the object of study. Treat it as a config value surfaced in
`run.json` and settable by CLI flag — never hardcoded.

Model choice is a known moderator: a different model could plausibly reverse a
language effect. Rather than pre-empting that with an expensive matrix, the MIT
license plus Harbor format _is_ the mechanism — document a one-command path for
third parties to contribute runs on other models, and define where those results
land (§7).

### 1.2 Pick the tier by discrimination, not by capability

Flagship tiers are poor value here. Within a model family, per-token price can
span an order of magnitude or more while agentic-coding capability spans a
couple of points. Since the model is a held-constant, buy "competent and
stable," not "maximal."

The stronger reason to go cheap: **statistical power peaks near a 50% pass
rate.** If every language passes every run, or fails every run, the experiment
measures nothing at any sample size — ceiling and floor effects destroy
discrimination outright. Model tier and task difficulty must therefore be
calibrated **jointly**, targeting roughly 40–60% pass rate in the _median_
language arm. A cheaper tier gives headroom to tune difficulty upward and budget
to run enough seeds.

### 1.2a Reasoning effort is a treatment, not a cost knob

Before using effort as a cheap dial, note that it plausibly sits on the causal
path. Effort settings change how much the model engages with tool output between
actions — and "does the agent convert a diagnostic into a correct edit" is
precisely the mechanism under study (§4). A low setting could suppress the very
behavior the experiment is designed to detect, producing a result that reads as
"types don't help" when it means "this configuration doesn't read compiler
output carefully."

Consequences:

- Pin the effort setting, record it in `model_settings`, and **scope every claim
  to it**: the finding is about that model at that effort, never about the model
  family.
- Measure the **malformed-action rate** during selection. Because mini-swe-agent
  does not use the tool-calling interface, the model must emit well-formed bash
  as plain text every turn; lower-effort modes are more prone to format drift.
  Critically, that drift is _not_ uniformly distributed — longer or more complex
  build invocations are more exposed, and invocation complexity correlates with
  language. Reject any rung whose malformed-action rate is non-trivial, and
  report the rate for the rung you keep.
- If effort ever becomes something you want to claim about, it is a separate
  crossed factor requiring its own design — not a byproduct of the selection
  ladder below.

### 1.2b Selection procedure: walk the ladder, don't pick a model

Do not choose the model first. Choose the **task** first, then walk a
cheapest-first ladder against a single median arm (Python or TypeScript),
roughly 3 seeds per rung. Effort is cheaper to step than tier, so alternate
accordingly:

| Rung | Configuration          |
| ---- | ---------------------- |
| 1    | `gpt-5.6-luna-low`     |
| 2    | `gpt-5.6-luna-medium`  |
| 3    | `gpt-5.6-terra-low`    |
| 4    | `gpt-5.6-terra-medium` |
| 5    | `gpt-5.6-sol-low`      |
| 6    | `gpt-5.6-sol-medium`   |

Procedure at each rung:

1. Run ~3 rollouts on the median arm. Record pass rate and malformed-action
   rate.
2. **Near 0%** → step up one rung.
3. **Near 100%** → the task is too easy. Harden the task; do not drop back down
   the ladder chasing the band.
4. **Malformed actions non-trivial** → step up (usually the effort step fixes
   it) and note the rung as unusable.
5. **Stop at the cheapest rung landing in the 40–60% band with clean action
   formatting.**

Publish the full ladder table with observed pass rates, not just the selected
rung. It is cheap, it documents the difficulty calibration, and it gives anyone
rerunning the artifact on a different model family a starting point. Total cost
is a few dozen rollouts weighted toward the cheapest tiers — close to free
against the real matrix.

The ladder is a **selection** procedure, not a comparison. It deliberately
crosses tier and effort, so nothing in it supports a claim about either factor;
its only output is a pinned configuration.

**A tension to resolve honestly, not paper over.** Step 3 says harden the task,
but the task is also supposed to be a realistic software-engineering change.
These goals conflict: you can always tune a task until it hits 50%, but a task
tuned for statistical convenience is no longer the realistic-codebase task the
design claims to test. The rule: adjust difficulty only within the range a real
maintainer would recognize as a plausible ticket. If no realistic task lands in
the band at any affordable rung, **report that as a finding about the model**
rather than reshaping the task until it cooperates.

### 1.3 Cost model and levers

Produce an explicit cost estimate before spending, as a formula with stated
assumptions, not a guess:

```
cost_per_rollout ≈ Σ_steps(prefix_tokens × effective_input_rate)
                 + total_output_tokens × output_rate
total ≈ cost_per_rollout × languages × seeds × task_families
```

Levers, in descending order of impact:

1. **Tier selection** — often the single largest factor.
2. **Prompt caching.** A linear-history agent resends the full prefix every
   turn, which is the ideal shape for caching; cache-read rates are typically an
   order of magnitude below input rates. **Verify caching is actually enabled
   and hitting before any paid run**, and log the observed cache hit rate — an
   unnoticed cache miss can multiply the bill.
3. **Step limit.** Set a hard cap and record `budget_exhausted` as a legitimate
   outcome rather than raising the cap.
4. **Seeds per cell** — cheapest to add, so tune last.

**Free by construction.** Calibration runs (reference solution, null run,
sabotage patches) and both mock agents involve _no model calls_. Debug the
entire pipeline at zero cost and spend money only once the harness is proven
green.

**Required gate:** a two-rollout cost pilot with measured (not estimated) token
counts, extrapolated to the full plan, before committing to any matrix.

---

### 1.4 Spend control: do not lose your pants

Cost accounting is a **feature of the harness**, not a post-hoc spreadsheet.
Implement all of the following before the first paid run.

**Provider-side hard cap is the real backstop.** Harness-side accounting cannot
stop a runaway if the harness crashes, if rollouts run in parallel sandboxes, or
if a retry loop misbehaves. Use a **dedicated API key created solely for this
experiment**, with a provider-configured hard spend limit set to the planned
budget plus a small margin. One key per experiment, revocable independently,
never a personal or shared key. This is the only control that holds when
everything else fails.

**Harness-side controls, all mandatory:**

- `--max-spend-usd` on the runner. Compute cost from _actual reported usage_
  after every rollout, accumulate to a persisted running total, and abort the
  whole run — not just the current rollout — when the ceiling is crossed.
  Persist the total to disk so a crash and restart cannot silently reset it.
- `--dry-run` that prints the projected cost of the planned matrix (cells ×
  seeds × measured cost-per-rollout) and exits without calling the model.
  Require it to be run and acknowledged before any paid execution.
- Hard per-rollout **step limit** and **wall-clock timeout**. These bound
  worst-case spend per cell; `budget_exhausted` is a legitimate recorded
  outcome, not a reason to raise the cap.
- Live running-total output after each rollout: spend so far, projected total at
  current burn rate, and remaining budget. A silent run is how bills get
  discovered late.
- **Fail closed on missing usage data.** If a response arrives without usage
  metadata, treat the rollout's cost as unknown and abort rather than continuing
  with untracked spend.

**Recording:** every `run.json` carries `measured_cost_usd`, `input_tokens`,
`output_tokens`, `cached_input_tokens`, `cache_hit_rate`, and the rate card used
for the calculation. Rate cards change; storing the assumed rates alongside the
token counts means costs can be recomputed later without guesswork. Emit a
per-experiment `spend_report.json` aggregating cost by language, by cell, and by
outcome — cost per _successful_ run is a genuine metric (§4), not just
bookkeeping.

**Order of operations, cheapest-first:**

1. Mock agents and the full calibration gate — **$0**, no model calls.
2. Two-rollout cost pilot with measured token counts → real cost-per-rollout.
3. `--dry-run` projection of the full matrix using that measured figure.
4. Model-selection ladder (§1.2b), weighted toward the cheapest rungs.
5. Full matrix, with `--max-spend-usd` armed.

If step 3's projection exceeds the budget, cut seeds before cutting calibration
or task realism.

## 2. Task Equivalence

Produce concrete, checkable guidelines covering: required behavioral changes;
number and conceptual complexity of affected concepts; repository size and
navigational complexity (files, modules, call depth to the change site);
persistence/state requirements; concurrency requirements; error-handling
surface; API boundaries; existing test coverage; volume of unfamiliar code the
agent must read.

Rules:

- **Never** define equivalence via equal LOC.
- **Never** force identical file layouts, APIs, or implementation strategies.
  Verbosity and compiler-induced work are _outcomes_, not nuisances to normalize
  away.
- **Produce an equivalence audit record** per task family: a structured file
  listing each dimension, its value per language, and every accepted discrepancy
  with a rationale. Record discrepancies; do not engineer them away.
- JS and TS share a lineage with a committed diff. Python and Go are authored
  independently and idiomatically.

---

## 3. Verification and the Calibration Gate

Verify observable behavior only: HTTP request/response, CLI invocation and
output, filesystem effects, database state, externally visible state
transitions. **Forbidden:** requiring specific class or function names unless
genuinely part of the public interface; AST inspection; requiring a particular
algorithm; inspecting internal data structures.

One language-neutral driver speaks the contract to all four implementations over
a process boundary, plus a thin per-language launch shim (build command, run
command, readiness probe, teardown). Use a **readiness probe with timeout, never
a fixed sleep**, and record startup duration as a separate metric rather than
folding it into the run budget.

**Visibility split:** the agent sees a behavior-focused prompt plus a small set
of developer tests covering the happy path. Hidden cases cover edge conditions,
error semantics, concurrency, and regression. State the exact split in the
design doc so difficulty is legible.

### The calibration gate (mandatory, blocking, free)

This is load-bearing. If the Go verifier is subtly stricter than the JS one,
every downstream number is meaningless and nothing else in the design would
reveal it. Verifier misgrading is a documented real problem — Datacurve's audit
of SWE-bench Pro found 8% false positives and 24% false negatives.

Before any paid run:

1. **Reference run** — known-good solution applied. Must pass **100%** of hidden
   cases in **all four** languages. Anything below 100% is a verifier or
   environment bug, not a finding.
2. **Null run** — no changes. Must fail, on the **same case IDs** across
   languages.
3. **Sabotage runs** — seeded plausible-but-wrong patches (off-by-one, missing
   error branch, wrong status code, unhandled concurrent update). Each must be
   caught by the **same case ID** in every language.

Note this is deliberately stronger than DeepSWE, where the reference patch is
held for offline human spot-checking and not used at grading time. Here,
verifier parity _is_ the experiment's validity, so automate it.

Emit `calibration_report.json`. No result record is valid without a green
report, and the report ships alongside published results.

---

## 4. Metrics

Capture raw data so metrics can be recomputed later.

**Correctness:** final pass/fail; percentage of cases passed; per-case results
with IDs; whether the first submitted solution passed; regressions in
pre-existing behavior.

**Agent effort:** turns; shell commands; files inspected; files modified; edit
operations; test/build/type-check invocations; failed cycles before first green.

**Tokens and cost:** input, output, cumulative; cache hit rate; max context
occupancy; tokens attributable to tool output; measured API cost.

**Latency confounds — instrument, don't merely disclaim:** wall-clock per
test/build/type-check invocation; byte and line count of diagnostic output per
invocation; time-to-first-signal after each edit; startup time;
dependency-install time and failure rate. Test-loop speed is a plausible causal
channel entirely independent of typing. Pre-register which confounds are
measured versus disclosed.

### Feedback-to-fix events (primary metric)

Operationalize "did type-checker feedback cause a correction?" mechanically:

> Diagnostic **D** is emitted at step _t_ naming location **L**; the agent's
> next edit touches **L**; a subsequent invocation of the same tool no longer
> emits **D**.

Record per run: count of such events; median steps from diagnostic to
resolution; diagnostics emitted and never resolved; edits at locations no
diagnostic named. Report the **rate** (resolved diagnostics per edit) alongside
absolute counts, so a language that simply emits more diagnostics isn't credited
for volume.

This is the most direct available evidence for the causal mechanism the study is
about. Ship an extraction script; mini-swe-agent's linear history makes it a
straightforward pass over the trajectory.

### Failure classification — two orthogonal fields

_Terminal stage_ (mutually exclusive): never-ran; failed-to-build-or-typecheck;
built-but-failed-dev-tests; passed-dev-tests-failed-hidden; regression-only;
budget-exhausted; harness-error.

_Root cause_ (may be multiple): syntax/parse; type/compile; dependency/build;
incorrect behavior; incomplete implementation; misunderstood requirement;
repository-navigation failure; environment/tooling failure; over-scoping or
collateral damage.

Every label needs an **evidence pointer** — a trajectory step index. State
whether labeling is manual, LLM-assisted, or both; if LLM-assisted, report
agreement against a human-labeled subset.

---

## 5. Controls

Same model and version; same agent and version; same system prompt; fresh
context per run; identical task wording except unavoidable language-specific
setup lines (quote those verbatim in the design doc); equivalent resource and
step limits; container images pinned by digest; no cross-run memory; randomized
or balanced execution order with `order_index` recorded; multiple independent
seeds per cell.

Do **not** statistically correct for presumed pretraining mass — there is no
independently measurable quantity to correct by. Document it as a limitation,
noting that the JS↔TS pair partially mitigates it since both are heavily
represented and share an ecosystem.

Do **not** normalize away verbosity or compiler-induced work. Report absolute
metrics plus patch statistics so readers can attribute effects themselves.

---

## 6. Statistical Structure (Be Honest About Small n)

Structure: **task family × language × typecheck_config × seed**.

**State plainly that the v1 prototype — one task family — can support no
conclusion about languages in general.** Its success criterion is that the
_pipeline_ produces fair, paired, interpretable measurements, evidenced by a
green calibration report. Anyone reading a language ranking off one task family
is misreading it, and the README should say so in those words.

Scaling guidance, with the reasoning stated: between-family variance almost
certainly dominates within-family seed variance, so **once past roughly 5 seeds
per cell, additional task families buy more inferential power than additional
seeds.** Propose a target (e.g. 8–12 families, 4 languages, 5–10 seeds) and
state the approximate detectable effect size on pass rate at that scale.

Aggregation:

- Analyze at task-family × language level; never collapse to a single benchmark
  score.
- Report full distributions and paired task-level differences, not just means.
- Headline test: mixed-effects logistic regression on pass/fail with random
  intercepts for task family; or, at small n, a paired bootstrap over families.
  Report intervals, not point estimates.
- Report per-family results in full even when they contradict the aggregate.
  Disagreement across families is itself a finding.

Questions the design must support:

- Does TypeScript complete more runs than JavaScript on the same family — and is
  the gap larger than between-family variance?
- Do typed variants hit more intermediate build failures but fewer hidden
  behavioral failures?
- Does static typing shift effort earlier without changing final correctness?
- Which languages consume more tokens or commands per _successful_ run?
- How often does type-checker feedback directly precede a successful correction
  (§4)?

---

## 7. Prototype

Build **one task family in all four languages**, end to end, in Harbor format,
runnable via Pier with mini-swe-agent.

### Task (use unless you can justify better)

**Add optimistic-concurrency control to an existing REST resource in a small
task-tracker service.**

Baseline: a working service with a persisted resource, full CRUD, and passing
tests. The concurrency feature is intentionally absent.

Required behavior: `GET` returns a stable `ETag` derived from resource state;
`PUT`/`PATCH` with `If-Match` succeeds only on match, returning `412` on
mismatch and `428` when the header is absent on a resource requiring it; a
matching write updates the tag; concurrent conflicting writes must not produce a
lost update; deleted resources behave correctly under stale tags.

It fits the criteria: requires reading existing code rather than writing a
standalone function; touches routing, handler, and persistence layers; carries
enough state for realistic subtle mistakes; exposes a purely HTTP contract;
verifiable by one shared driver; tests HTTP semantics rather than framework
trivia.

_If the stateless-shell issue (§0.2) makes the HTTP variant awkward, fall back
to:_ idempotency-key support on a `POST` endpoint (dedupe window,
stored-response replay, conflict on payload mismatch), exposed via CLI.

### Layout

```text
tasks/
  optimistic-concurrency/
    javascript/ typescript/ python/ go/    # each in Harbor format
    verifier/                              # shared driver + per-language shims
    calibration/                           # reference solution + sabotage patches
    EQUIVALENCE.md                         # completed audit
analysis/                                  # feedback-to-fix extraction, aggregation
results/
  <model>/<date>/                          # run.json + events.jsonl per rollout
docs/
LICENSE                                    # MIT
```

Ship **two mock agents** — one that solves, one that fails plausibly — so the
pipeline is exercised in both directions at zero cost.

Define the contribution path for third-party runs on other models: where results
land, what metadata is required, and what makes a submission valid (green
calibration, pinned image digest, published trajectories).

---

## 8. Result Schema

Two artifacts, versioned:

- **`run.json`** — one summary record per rollout.
- **`events.jsonl`** — append-only event log (every command, edit, diagnostic,
  token delta), referenced by index from the summary.

Summary fields: `schema_version`; `benchmark_version`; `task_family`;
`language`; `typecheck_config`; `repo_revision`; `container_image_digest`;
`model`; `model_settings` (including reasoning effort); `scaffold`;
`agent_version`; `pier_version`; `malformed_action_count`; `run_id`; `seed`;
`order_index`; toolchain versions; start/end timestamps; `verifier_case_results`
(case ID + pass/fail + duration); `regression_results`; `calibration_ref`; token
usage; `cache_hit_rate`; `measured_cost_usd`; command counts;
`feedback_to_fix_events`; patch statistics; `terminal_stage`; `root_causes` with
evidence pointers; `stopped_reason`; `exit_status`.

Never collapse a run to a single numeric score anywhere in the schema.

---

## 8a. Deferred: variants to add when budget and time allow

Listed in priority order. Each is additive — the v1 schema must accommodate all
of them without migration.

1. **Within-language strictness ladder.** Adds JS + JSDoc + `checkJs: true`;
   Python + pyright; TS `strict: false`. Converts the fragile between-language
   comparison into a within-language dose–response curve and is the principal
   defense against the Go confound noted in §0.1. Highest scientific value per
   dollar of anything on this list.
2. **A second scaffold arm** (claude-code or codex via Pier) over the same task
   variants, per §0.2a. Tests whether the scaffold mediates the language effect.
3. **Additional task families.** Past roughly 5 seeds per cell, more families
   buy more inferential power than more seeds (§6).
4. **A second model family**, ideally contributed by third parties via the MIT
   artifact rather than self-funded.
5. **Reasoning-effort as a crossed factor**, if §1.2a's concern proves
   substantive — requires its own design, not a byproduct of the selection
   ladder.

## 9. Deliverables

1. Four Harbor-format task variants sharing one behavioral contract.
2. Shared behavioral verifier with per-language shims.
3. Calibration script and a green `calibration_report.json`.
4. Feedback-to-fix extraction and aggregation scripts.
5. README: one-command run instructions, cost estimate with stated assumptions,
   and an explicit statement of what v1 results can and cannot support.
6. Design document, including the DeepSWE comparison, the confound structure of
   §0.1, and the scaffold-validity argument of §0.2a stated as a limitation
   rather than resolved.
7. Task-equivalence guidelines plus the completed audit.
8. Result schema and example records from both mock agents.
9. MIT license and third-party contribution path.
10. `spend_report.json` and documented API-key hygiene (dedicated key,
    provider-side hard cap).
11. Threats to validity, and the next 3–5 task families, each with a one-line
    rationale for what it isolates that the first does not.

## Acceptance criteria

- Calibration green: reference at 100% in all four languages; null and sabotage
  runs fail on identical case IDs.
- The same verifier driver runs unmodified against all four implementations.
- `pier run` against a mock agent produces schema-valid `run.json` and non-empty
  `events.jsonl`.
- Feedback-to-fix events extractable from `events.jsonl` by a shipped script.
- Measured two-rollout cost pilot, extrapolated, appears in the README.
- `--dry-run` prints a full-matrix cost projection and exits without model
  calls.
- `--max-spend-usd` demonstrably aborts a run mid-matrix, with the running total
  persisted across a restart.
- Exactly four cells in v1: JS/`none`, Python/`none`, TS/`strict`, Go/`default`.
- The model-selection ladder table (§1.2b) is published with observed pass rates
  and malformed-action rates per rung.
- The design document states plainly that the bash-only scaffold is one arm of a
  planned two-arm design, and names what it cannot license.
- Net new code is task variants, verifier, calibration, and analysis — no
  reimplemented harness.

If any requirement here is internally inconsistent or forces an unsound
experimental choice, say so explicitly and propose an alternative rather than
silently resolving it.
