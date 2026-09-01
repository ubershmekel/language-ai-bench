# Experimental design

## Contribution and estimand

[DeepSWE](https://github.com/datacurve-ai/deep-swe) already uses Harbor tasks,
Pier, and mini-swe-agent across several languages, but its language tasks come
from different repositories and domains. Language is therefore confounded with
task/repository difficulty. This project's core contribution is matched task families that hold behavior
constant across language variants. v0.3 adds a focused JS/TS decision study
crossed with greenfield and brownfield starting conditions. DeepSWE holds reference solutions for review;
here reference execution is automated because verifier parity is the validity
gate.

The primary estimand is the paired TypeScript-strict minus JavaScript-no-types
effect for a fixed model, effort, scaffold, task family, and seed policy.
Python and Go are descriptive external-validity probes. In particular, a Go–JS
difference cannot be attributed to typing rather than blocking compilation,
ecosystem, diagnostic quality, loop latency, or pretraining mass.

The `python-typed` arm is the within-language answer to that confound: the same
interpreter, standard library, and file topology as `python`, differing only in
annotations and a blocking `mypy --strict` step in the developer loop. Its
paired contrast against `python` is the one comparison in this repo where the
treatment is typing alone, so it carries more internal validity than any
cross-language pair including JS/TS, which still differ in compile step and
build tooling. It is reported as a second primary estimand, not a probe.

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
fixed sleeps. Each family keeps its receipt in `calibration/`.

Instructions must not enumerate what the hidden tests cover. Three of them used
to, which handed the agent a checklist of exactly what the grader looks at. That
line is gone from `money-rollup`, `circuit-breaker`, and `configuration-merge`
as of task text revision v1.0; `text-redact` keeps its copy because it is frozen
around a published result. Family pass rates are comparable only within a repo
revision, and `tasks/FAMILIES.md` records which families are active, retired, or
unadmitted, and why.

The free gate proves the scoring is fair, not that the task is hard.
`text-redact` passed it in all five languages, its untouched starter failed ten
of twelve checks, and it still passed 39 of 40 paid attempts with its intended
hazard never firing. A new family therefore also has to clear a paid difficulty
probe before it joins a cohort: ten rollouts at the target rung, two per
language, with the family's admission threshold written down before the first
call. Admit the family only if it passes at most seven of ten. At recent
per-rollout cost that probe is about $0.06 and it protects a 40-rollout family
block. The probe is a go/no-go on the family, it is reported separately, and its
rollouts are never pooled into a cohort result.

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
tickets. The cheapest rung, GPT-5.6 Luna at low effort, completed all 22 balanced runs
without command-format exceptions. The original and hardened task families both
reached 100% correctness. Stronger model rungs were not run because model selection was complete; continuous efficiency and workflow outcomes remain informative. `model_selection_ladder.json`
records that stopping decision.

## Threats and next families

- Task representativeness: two related backend HTTP contracts are not a language ecosystem.
- Scaffold mediation: bash choice/invocation behavior can mask type benefits.
- Runtime/ecosystem/pretraining confounding outside the JS/TS matched pair.
- The 2026-08-24 cohort predates source-format and topology audits; its efficiency telemetry is historical and confounded. Correctness remains valid for the tested contracts.
- Calibration sabotage modes are deliberate fault injections, not empirical
  frequencies of real agent mistakes.
- Mock runs prove plumbing only and contain no performance evidence.

`circuit-breaker` was added after the v0.7 failure table showed `money-rollup`
discriminating on numeric semantics and specification breadth rather than on
anything a checker sees: its failing cases were rounding mode, negative-zero
formatting, and rejection coverage, and the untyped language swept it. The new
family routes difficulty through a three-state machine and a three-variant
outcome union consumed across module boundaries, where a missed case is silent
in JavaScript and Python and visible to tsc, go build, and mypy. Its clock is an
explicit `at` field on every call, so verification is deterministic without
sleeps. A scan of DeepSWE's 113 tasks informed the shape: its hardest tasks
combine many interacting rules rather than one hard algorithm, and its terse
prompts over large real repos make navigation a difficulty lever this repo
cannot use without reintroducing ecosystem confounds.

`text-redact` was added after v0.8 showed those two families ranking the arms
in nearly opposite orders. Each ordering follows from the affordance the family
rewards, so a third family that repeated either mechanism could not break the
tie. This one turns on what a string is at runtime: every offset and length in
its contract counts Unicode code points, which Python indexes already,
JavaScript and TypeScript do not, and Go forces into the open as string against
[]rune. tsc and mypy report nothing about the distinction, so it is the first
family where the three checked arms have no reason to behave alike. Its
calibration sabotages are all logic-level on purpose: a sabotage that swapped
code points for UTF-16 units would be a no-op in Python and so could never be
caught by the same case ids everywhere, which the parity gate forbids.

v0.9 ran that family and it saturated: 39 of 40 passes, and zero runs failed
either hidden case that catches offsets counted in UTF-16 code units or bytes.
The instruction was the cause. It titled the task after the hazard, gave the
code point rule a paragraph of its own ending in a sentence saying it does not
matter how your language indexes a string, and closed by naming the two hidden
cases. Every language converted to a code point sequence before writing any
logic. `redact-spans` is the revision. It states the unit once, where each field is
defined, and drops the title, the paragraph, and the list of hidden cases. It
also widens where the hazard can fire: `astral-literal-scan` is a new hidden
case whose literal is itself an astral string, and `merge-touching` and
`min-length-drops-before-merge` run over astral text. Changing the one code
point conversion in the JavaScript reference to `text.split("")` fails seven of
the thirteen cases in `redact-spans` against four of twelve in `text-redact`.
The developer tests stay ASCII only, which is what makes the hidden cases worth
running. It carries a new family id because it is a different task, and
`text-redact` is left untouched so the v0.9 cohort stays reproducible; pass
rates under the two ids are not comparable.

The probe then said no. Ten rollouts, two per language, all ten passed, none
failed a wrong-unit case, $0.052132 measured. So the instruction was not what
made v0.9 saturate, and hiding the hazard better is not the lever. At this rung
the model counts code points correctly in every language unprompted. The
remaining honest lever is task size, which is where the DeepSWE comparison
already pointed: 844 reference patch lines against 301 here, and 15 instruction
lines against 69. `redact-spans` stays in the tree, gate green and unadmitted,
as the receipt for that. `docs/REDACT_SPANS_PROBE.md` is the report.

`expr-eval` is the first family built to a different size. Every other family
states its whole contract in a 69 to 82 line instruction over a reference of
about 300 lines. DeepSWE's median is the other way round: a 15 line instruction
over an 844 line patch. Two saturation results in a row, `text-redact` and then
`redact-spans`, say that hiding a hazard inside a small task does not make it
hard, so this one moves the size instead. The ticket is eight lines and points
at `SPEC.md` in the workspace; the reference is a tokenizer, a precedence
climbing parser, and an evaluator.

Its affordance is a fourth one: what an integer is. The contract is signed
64-bit two's complement. Go gets that from `int64`, truncating division and
arithmetic shift, and only has to read literals as `uint64` and reinterpret.
Python has to wrap every result and write truncating division itself, because
`//` floors and `%` follows the divisor. JavaScript and TypeScript have to use
`BigInt` throughout, because `number` stops being exact at 2^53 and the bitwise
operators are 32 bits wide, and they cannot use `JSON.stringify` on the result.
`tsc` reports `bigint` against `number` and nothing else; `mypy` reports none of
it. Go having the least to do is the opposite of `money-rollup`, which is why
the two are worth running together.

Next families: schema migration with backward-compatible reads (static schema
feedback); streaming parser recovery (sum types/error handling); dependency API
migration (navigation and ecosystem knowledge); bounded worker queue
(concurrency without HTTP).

## Internally inconsistent acceptance boundary

“`pier run` against a mock agent produces this custom `run.json`” conflicts with
“do not write a harness” unless a specific Pier version/import adapter is pinned:
Pier emits its own job/ATIF layout. This prototype preserves Harbor inputs and
tests the custom schema with a local zero-model mock pipeline; real execution is
delegated to Pier and imported losslessly. Likewise, measured paid cost and an
observed model ladder cannot be produced without an authorized capped key. Both
gates remain visibly incomplete instead of being filled with invented numbers.
