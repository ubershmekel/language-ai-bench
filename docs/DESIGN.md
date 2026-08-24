# Experimental design

## Contribution and estimand

[DeepSWE](https://github.com/datacurve-ai/deep-swe) already uses Harbor tasks,
Pier, and mini-swe-agent across several languages, but its language tasks come
from different repositories and domains. Language is therefore confounded with
task/repository difficulty. This project's contribution is one matched task
family implemented four ways. DeepSWE holds reference solutions for review;
here reference execution is automated because verifier parity is the validity
gate.

The primary estimand is the paired TypeScript-strict minus JavaScript-no-types
effect for a fixed model, effort, scaffold, task family, and seed policy.
Python and Go are descriptive external-validity probes. In particular, a Go–JS
difference cannot be attributed to typing rather than blocking compilation,
ecosystem, diagnostic quality, loop latency, or pretraining mass. The deferred
within-language strictness ladder is the main defense against that confound.

## Scaffold validity

mini-swe-agent's bash-only linear history is one planned scaffold arm, not a
neutral container. Its plain-text action interface can change malformed-command
rates and editing ergonomics. More importantly, it exposes compiler feedback
only when the agent chooses to run a CLI checker. A null result could therefore
mean “the agent did not invoke/read the checker,” not “types did not help.”

CLI diagnostics nevertheless resemble how many current coding agents obtain
type feedback, while richer edit/retrieval/LSP layers introduce their own
language-specific fidelity. The bash-only arm licenses only: “holding this
neutral-ish scaffold fixed, language X differed by Z.” A later Codex or
Claude-Code Pier arm licenses claims about real deployed scaffolds. Agreement is
robustness; disagreement is evidence that scaffold mediates the language
effect. DeepSWE itself uses a fixed mini-swe-agent methodology; Pier also
supports Codex, Claude Code, Gemini CLI, and OpenCode.

## Controls and instrumentation

Fix model snapshot, effort, agent/Pier versions, system prompt, step/time/memory
limits, image digest, wording, and fresh context. Balance randomized order and
record `order_index`; use independent seeds and no cross-run memory. Do not
normalize verbosity or compiler work and do not statistically “correct” for
unmeasurable pretraining mass.

Record command/edit/test/build counts; invocation wall time; diagnostic bytes
and lines; time from edit to first signal; startup/dependency time and failures;
tokens, cache reads, context occupancy, and cost. Measured confounds are startup
and invocation latency/output volume. Disclosed-only confounds in v1 are
ecosystem quality and pretraining exposure.

Feedback-to-fix is mechanical: diagnostic D at location L, next edit touches L,
then the same tool no longer emits D. Report count, median steps, unresolved
diagnostics, non-diagnostic edits, and resolved diagnostics/edit. The extractor
uses the append-only event stream.

Terminal stage is mutually exclusive; root causes are multi-label. Every cause
points to an event index. v1 labels are manual for real runs and deterministic
for mocks. If LLM-assisted labeling is later used, report agreement on a
human-labeled subset.

## Calibration and statistics

The blocking free gate requires reference 100% in all languages, identical null
failure IDs, and identical failure IDs for off-by-one, missing-branch,
wrong-status, and non-atomic-update sabotages. It uses readiness probes, never
fixed sleeps. `calibration_report.json` is the receipt.

Analyze at task-family × language level, report full distributions and paired
differences. With multiple families use a paired bootstrap, or mixed-effects
logistic regression with task-family random intercepts. Intervals matter more
than point estimates. After about five seeds/cell, add families: between-family
variance should dominate. A target of 10 families × 4 languages × 8 seeds (320
runs) has a rough independent-binomial standard error near 5.6 percentage
points at p=.5 per language; paired structure can improve or worsen this based
on cross-language correlation, so simulation from pilot data must set the real
detectable effect. One family supports no language-general conclusion.

The cheapest-first selection ladder is recorded in
`model_selection_ladder.json`. Effort is pinned treatment metadata, not a casual
cost dial. Reject rungs with non-trivial malformed actions; stop at the cheapest
clean 40–60% rung. Difficulty may change only within plausible maintainer
tickets. No paid key was supplied, so observations are intentionally null.

## Threats and next families

- Task representativeness: one HTTP concurrency ticket is not a language.
- Scaffold mediation: bash choice/invocation behavior can mask type benefits.
- Runtime/ecosystem/pretraining confounding outside the JS/TS matched pair.
- Calibration sabotage modes are deliberate fault injections, not empirical
  frequencies of real agent mistakes.
- Mock runs prove plumbing only and contain no performance evidence.

Next families: schema migration with backward-compatible reads (static schema
feedback); streaming parser recovery (sum types/error handling); dependency API
migration (navigation and ecosystem knowledge); bounded worker queue
(concurrency without HTTP); configuration merge semantics (data-shape and
property-based edge cases).

## Internally inconsistent acceptance boundary

“`pier run` against a mock agent produces this custom `run.json`” conflicts with
“do not write a harness” unless a specific Pier version/import adapter is pinned:
Pier emits its own job/ATIF layout. This prototype preserves Harbor inputs and
tests the custom schema with a local zero-model mock pipeline; real execution is
delegated to Pier and imported losslessly. Likewise, measured paid cost and an
observed model ladder cannot be produced without an authorized capped key. Both
gates remain visibly incomplete instead of being filled with invented numbers.
