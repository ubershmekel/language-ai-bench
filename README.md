# Language AI Bench

A minimal, MIT-licensed experiment asking one question:

> **How does programming-language choice, and especially the feedback a type
> system and its standard tooling provide, affect an autonomous coding agent's
> ability to complete the *same* software-engineering task?**

The design must be able to answer "typing hurts" and "no effect detectable at
this sample size." Both are acceptable findings. A benchmark that can only
discover the result its author expects is not measuring anything.

## The cells

| Language | `typecheck_config` | Feedback |
|---|---|---|
| JavaScript | `none` | none |
| TypeScript | `strict` | structural, thorough |
| Python | `none` | none |
| Python (typed) | `mypy-strict` | structural, in the developer loop |
| Go | `default` | compiler, blocking |

**Do not read this as a leaderboard.** JavaScript↔TypeScript is
the matched pair and the analytical centerpiece: same runtime, package manager,
test runner, ecosystem idioms, and error-message conventions, so the type layer
is close to the only varying factor. Python and Go widen external validity but
carry confounds: different ecosystems, diagnostic quality, test-loop latency,
and pretraining mass. A Go-versus-JavaScript difference cannot be attributed to
*typing* rather than to compilation, tooling, or ecosystem.

**Two of these pairs are the same language with and without types.**
JavaScript and TypeScript are one such pair, and Python and typed Python are
the other. The Python pair is the tighter of the two: TypeScript adds a compile
step and a build toolchain on top of the types, while typed Python is the same
interpreter running the same files, with annotations and `mypy --strict` as the
only difference. Reading both pairs together separates "types helped" from
"having a build step helped". `verify-local` runs `mypy` before the developer
tests, so that feedback is actually in the loop rather than merely available.

## What this contributes over DeepSWE

[DeepSWE](https://deepswe.datacurve.ai/) covers 113 tasks across TypeScript
(35), Python (34), Go (34), Rust (5), and JavaScript (5), but each task comes
from a *different real repository*. Language is fully confounded with repo,
domain, and difficulty, so no language effect is readable from its leaderboard.

**The matched task family is the contribution here.** One behavioral contract,
authored idiomatically in every language, verified by one language-neutral
driver, with a blocking calibration gate proving the verifier is equally strict
everywhere.

Two calibration facts from that corpus are worth carrying:

| | DeepSWE | this repo (`money-rollup`) |
|---|---|---|
| Reference solution | 844 patch lines (median) | 301 lines |
| Instruction | 15 lines (median) | 69 lines |
| Agent timeout | 10800s | 1800s |
| gpt-5.6-luna, low effort | ~2% | 88% |

DeepSWE's tasks are terse prompts over large real repos: difficulty comes from
underspecification and navigation. That lever is unavailable here, because
navigation and convention-inference vary by ecosystem and would reintroduce the
confound this repo exists to remove. The lever available is **specification
breadth**: many interacting rules, each individually easy, collectively easy to
leave one out.

## Verification

Verify **observable behavior only**: CLI invocation and output, HTTP
request/response, filesystem effects, externally visible state transitions.
Forbidden: requiring particular class or function names unless genuinely part of
the public interface, AST inspection, requiring a specific algorithm, inspecting
internal data structures. Verbosity and compiler-induced work are *outcomes* to
be measured, never nuisances to normalize away. Task equivalence is never
defined by equal lines of code.

The agent sees a behavior-focused prompt plus developer tests covering the happy
path. Hidden cases cover edge conditions, error semantics, and regressions.

### The calibration gate (mandatory, blocking, free)

If one language's verifier is subtly stricter than another's, every downstream
number is meaningless and nothing else in the design would reveal it. Before any
paid run, and costing nothing:

1. **Reference run**: 100% of hidden cases in every language. Below 100% is a
   verifier or environment bug, not a finding.
2. **Null run**: the untouched starter must fail on the *same case IDs* in
   every language.
3. **Sabotage runs**: seeded plausible-but-wrong patches, each caught by the
   *same case ID* in every language.

`calibration_report.json` is the receipt. No result is valid without a green one.

### Feedback-to-fix is the primary mechanism metric

Pass rates say whether types helped; they do not say *how*. The mechanism is
defined mechanically: diagnostic **D** is emitted at step *t* naming location
**L**, the agent's next edit touches **L**, and a later run of the same tool no
longer emits **D**. Recorded per run as a count, a median step distance, and a
rate per edit, so a language is not credited merely for emitting more
diagnostics. This distinguishes "the compiler cost extra steps" from "the
compiler converted a diagnostic into a fix", a distinction step counts alone
cannot make.

## Task families

| Family | Contract | What it isolates |
|---|---|---|
| `optimistic-concurrency` | HTTP | ETag/If-Match state transitions |
| `task-service-greenfield` | HTTP | the same contract, built from scratch |
| `schedule-variants` | HTTP | brownfield and greenfield, once/interval schedules |
| `configuration-merge` | CLI | data-shape and precedence edge cases |
| `money-rollup` | CLI | exact arithmetic, graph search, a wide rejection surface |
| `circuit-breaker` | CLI | a state machine and an outcome union crossing module boundaries |
| `text-redact` | CLI | Unicode code point offsets, which no checker sees |
| `redact-spans` | CLI | the same contract with the hazard not announced, unadmitted |
| `expr-eval` | CLI | 64-bit two's complement integers, an 8 line ticket over a workspace spec |

## History

v0.1 shipped one optimistic-concurrency family. v0.4 added a JavaScript/
TypeScript decision study crossed with greenfield and brownfield starts; the
staged cells and stopping budget are in `decision_benchmark.json`. The v0.6
cohort balanced all four languages at nine brownfield runs each across three
families, and all 36 passed. A benchmark whose tasks are all solved cannot
answer whether the language matters.

`tasks/money-rollup` exists to break that ceiling: a four-file brownfield
refactor replacing floating-point money handling with exact rational arithmetic,
adding shortest-path conversion with ambiguity rejection, ancestor rollups, and
a large rejection surface. On the strong rung it passes 84/96 rather than
everything, so contrasts are finally estimable. Python passed all 24 attempts,
TypeScript 22, Go 20, JavaScript 18; the Python advantage over JavaScript and
over Go has intervals clear of zero. Effort separates further: Go needed about
1.5 more agent steps than Python or JavaScript, TypeScript about 0.7 more. On a
weaker model the same task is a cliff no language rescues.

## v0.8: the families disagree

`python-typed` and `circuit-breaker` were added to answer v0.7 on its own
terms. 120 rollouts, $0.64 measured.

**Adding types to Python did not measurably help.** Typed Python passed 19 of
24 and untyped Python 18 of 24. The gap is +0.042 with a 95% interval of
[-0.125, 0.208], which spans zero, so at this sample size the difference is
indistinguishable from chance. That is a real answer, not a failed experiment.

**The interesting finding is that the two hard families rank the arms in nearly
opposite orders.**

| Family | Ordering |
|---|---|
| `circuit-breaker` | Go 7/8 > TypeScript 6/8 > JavaScript 4/8 > Python (typed) 3/8 > Python 2/8 |
| `money-rollup` | Python 8/8 > Python (typed) 8/8 > Go 6/8 > TypeScript 6/8 > JavaScript 5/8 |

Python is the best arm on one and the worst on the other. This is what the
warning against leaderboards looks like when it actually bites: pooling these
produces an aggregate describing neither, and a single benchmark score would
have hidden it. It is also consistent with how the families were designed:
`money-rollup` rewards exact-arithmetic affordances (Python's `fractions`),
while `circuit-breaker` rewards exhaustiveness over a state machine and an
outcome union, where the compiled and checked arms lead.

Effort reproduces v0.7's direction: JavaScript needed fewer agent steps than
TypeScript, typed Python, and Go, and Python fewer than Go, all with intervals
clear of zero.

## v0.9: the third family was too easy

`text-redact` was built to break the v0.8 tie. It specifies every offset and
length in Unicode code points, which Python indexes already, JavaScript and
TypeScript do not, and Go forces into the open as `string` against `[]rune`.
Neither `tsc` nor `mypy` says anything about the difference, so it was the first
family where the three checked arms had no reason to behave alike.

**It did not work.** 120 rollouts, $0.70 measured. `text-redact` passed 39 of
40, and of those 40 runs, zero failed either of the two hidden cases that catch
offsets counted in the wrong unit. The trap never sprang. The likely cause is
plain: the instruction states the code point rule in its own paragraph and adds
that it does not matter how your language indexes a string, which is a loud
warning sitting directly on the hazard. A green calibration gate proves the
scoring is fair in every language. It does not prove the task is hard.

**The obvious fix did not work either.** `redact-spans` is the same contract
with the signposting removed: no title naming the hazard, no paragraph of its
own, no closing line listing the hidden cases, the unit stated once where each
field is defined, and three more hidden cases that a wrong unit breaks. Changing
the one code point conversion in the JavaScript reference to `text.split("")`
fails seven of its thirteen cases against four of twelve before. A
pre-registered ten-rollout probe, two per language, then passed 10 of 10 with
zero wrong-unit failures for $0.052. So the instruction was not the binding
constraint. At this rung the model counts code points correctly in every
language without being told to, and hiding the hazard better is not the lever.
`redact-spans` stays in the tree, gate green and unadmitted, as the receipt.
[docs/REDACT_SPANS_PROBE.md](docs/REDACT_SPANS_PROBE.md) is the report.

The two carried-over families disagree, and the cohort produced a second
result worth more than the one it was designed for. Both were rerun with
nothing changed but the randomization seed:

| Family | Arm | v0.8 | v0.9 |
|---|---|---:|---:|
| `circuit-breaker` | TypeScript | 6/8 | 2/8 |
| `circuit-breaker` | Go | 7/8 | 4/8 |
| `circuit-breaker` | JavaScript | 4/8 | 6/8 |
| `money-rollup` | Python | 8/8 | 6/8 |
| `money-rollup` | Go | 6/8 | 4/8 |

Eight attempts per cell does not fix a per-family ordering. What reproduces is
the weaker and more useful claim: the families disagree, and no arm leads on
all of them. What does not reproduce is the exact order inside either family,
so the v0.8 orderings above should be read as one draw, not as a ranking. The
typed-Python contrast came out at +0.125 with a 95% interval of [-0.125, 0.375],
spanning zero again.

Read [docs/V09_REPORT.md](docs/V09_REPORT.md),
[docs/V08_REPORT.md](docs/V08_REPORT.md) and
[docs/V07_REPORT.md](docs/V07_REPORT.md). The historical
[docs/V06_REPORT.md](docs/V06_REPORT.md),
[docs/POLYGLOT_REPORT.md](docs/POLYGLOT_REPORT.md), and
[docs/DECISION_REPORT.md](docs/DECISION_REPORT.md) preserve prior reports, and
older cohorts are never pooled with v0.7 estimates.

Caveat carried from that report: the strong rung was collected in two batches of
48, and the second was run *because* the first left the Python-versus-Go
interval touching zero. That makes the continuation outcome-dependent. Twelve
attempts per language is not many.

## Run it on Linux (or Docker Desktop's Linux engine)

Requirements: Docker and Python 3.11+. No language toolchains on the host.
Base-image digests resolved during calibration are recorded in
`images.lock.json`; published runs must put their built image digest in
`run.json`.

```bash
sh scripts/run-local.sh
```

That builds and behaviorally exercises every real implementation, runs
reference/null/sabotage calibration, creates passing and failing zero-cost mock
rollouts, and prints per-cell aggregation. Direct commands:

```bash
python3 scripts/calibrate.py --task-dir tasks/circuit-breaker --languages javascript typescript python python-typed go
```

`run-local.sh` calibrates one family across all five arms as a smoke test. Each family has its own receipt at the repository root; run `calibrate.py` per family to regenerate them.

```bash
python3 scripts/run_benchmark.py --agent mock-solve --seeds 2 --max-spend-usd 10 --dry-run
```

```bash
python3 analysis/aggregate.py results
```

`scripts/verify-local` in every variant starts the service, readiness-probes,
tests, and tears down in one shell invocation. This resolves mini-swe-agent's
non-persistent-shell asymmetry, which would otherwise land differentially across
languages: `go build && ./server &` is a different experience from
`npm run dev &`, and that asymmetry would sit directly on the dependent
variable.

## The scaffold is a treatment, not a neutral container

mini-swe-agent is bash-only with a linear history: no tool-calling interface, so
no language-specific affordances are baked into the scaffold, and the trajectory
*is* the message list, which makes feedback-to-fix events extractable rather
than reconstructed.

But it exposes type information only when the agent *chooses* to run `tsc` or
`go build` and read the output. A null result could therefore mean "the agent
did not invoke the checker," not "types did not help." Two things partly defend
the choice: CLI invocation is how most production coding agents actually obtain
type feedback today, and any richer scaffold bakes third-party, per-language
tool quality into the apparatus. An LSP hands TypeScript and Go far richer
information than JavaScript and Python, which *is* the treatment, implemented by
someone else with unmeasured fidelity.

So `scaffold` is a first-class run variable. The bash-only arm licenses only
"holding this scaffold fixed, language X differed from Y by Z." A second arm
through a real agent would license claims about deployed scaffolds. Agreement
across arms is robustness; disagreement would mean the scaffold *mediates* the
language effect, which is the more interesting result. DeepSWE names this same
fixed-harness constraint as a known limitation.

## Real agents through Pier

For secret setup, the two-rollout cost pilot, and the publication boundary,
follow [the paid-run guide](docs/RUNNING_PAID.md). Install
[Pier](https://github.com/datacurve-ai/pier), then run one Harbor task directory
with a fresh context per seed:

```bash
pier run -p tasks/optimistic-concurrency/typescript --agent mini-swe-agent --model YOUR_PROVIDER/YOUR_MODEL
```

Pier, not this repository, owns sandboxing, model calls, network allowlists,
timeouts, and trajectories. This artifact intentionally does not wrap or
reimplement it. **Explicitly not built here:** a harness, a sandbox layer, a
trajectory viewer, an agent framework, a results database, or a web UI. Net new
code is task variants, one shared verifier, calibration, and analysis.

## Spend gate

Use a dedicated experiment-only API key with a provider-side hard limit equal to
planned spend plus a small margin. Never a personal or shared key. The provider
cap is the only control that survives concurrent sandboxes or a runner crash.

```text
rollout = sum(step_prefix_tokens × effective_input_rate) + output_tokens × output_rate
matrix  = rollout × languages × seeds × task_families
```

The v0.6 cohort cost $0.19101201 for 36 valid completions; the v0.7 cohort cost
$1.00391751 for 121. The v0.8 pilot measured $0.00581969 per rollout and its
120-rollout matrix came in at $0.644634. The v0.9 pilot measured $0.00591306 and
its 120-rollout matrix came in at $0.699961, four at a time in about two hours.
`studies/cost_pilot.json`, `studies/cost_pilot_v0.8.json`, and
`studies/cost_pilot_v0.9.json` store the
pilots. Calibration, both mock agents, and the null
and sabotage runs involve **no model calls**, so debug the entire pipeline at zero
cost and spend only once the gate is green.

## Statistical structure

Structure is task family × language × `typecheck_config` × seed. Analyze at
family × language level and never collapse to a single benchmark score. Report
full distributions and paired differences with intervals, not point estimates,
and report per-family results in full even when they contradict the aggregate.
Disagreement across families is itself a finding.

Past roughly five seeds per cell, **additional task families buy more
inferential power than additional seeds**, because between-family variance
almost certainly dominates within-family seed variance. One family supports no
language-general conclusion.

Statistical power peaks near a 50% pass rate. Ceiling and floor effects destroy
discrimination outright at any sample size, so task difficulty and model tier
are calibrated *jointly*, targeting the 40–60% band in the median arm. Difficulty
may be adjusted only within the range a real maintainer would recognize as a
plausible ticket; if no realistic task lands in the band at any affordable rung,
that is a finding about the model, not a licence to reshape the task.

## v1.0: the task decides which language wins

**119 scored rollouts, $0.849144 measured.**

| Task | Spread | Ordering |
|---|---:|---|
| `expr-eval` | 7 runs | JavaScript 7/8 > Python 4/8 ~ Python (typed) 4/8 ~ TypeScript 3/8 > Go 0/8 |
| `circuit-breaker` | 6 runs | Go 8/8 > TypeScript 5/8 ~ JavaScript 4/8 ~ Python (typed) 4/8 > Python 2/8 |
| `money-rollup` | 1 run | Python (typed) 8/8 ~ TypeScript 7/7 ~ Go 7/8 ~ JavaScript 7/8 ~ Python 7/8 |

Setups within a run of each other are written as tied, `~`: eight attempts
cannot separate them.

Two tasks, two different winners, and that is the expected result. A type
system is not one lever, and these tasks fail for different reasons.

`circuit-breaker` fails when a case of a union that crosses files gets dropped.
That is a shape a checker can see, and `go build`, `tsc`, and `mypy` all name
the missing case at the point of the mistake. Go passes 8 of 8; Python, which
reports nothing, passes 2 of 8.

`money-rollup` ties across every setup here, so it ranks nothing this round.
What it fails on is rounding mode, negative zero formatting, and which
conversion path was taken. Every one of those type checks cleanly while being
wrong, because `half-up` and `half-even` have the same type. No checker helps
there; having exact rational arithmetic in the standard library does.

`expr-eval` specifies signed 64-bit two's complement integers. JavaScript has
no such type, so the model has to make a visible decision, reach for `BigInt`,
and mask to 64 bits: 7 of 8. Go has that arithmetic already in `int64`, which
turns out to be the trap. It missed the parts that are not free, reading a
literal as `uint64` before reinterpreting it, checking a shift count, and
spelling complement `^x` where the contract writes `~x`, while spending the most
steps of any setup at 13.25 against JavaScript's 8.25. It passes 0 of 8.

So a type system pays when the bug is a shape and not when the bug is a value or
a convention. Both kinds are ordinary, and which kind a ticket contains is not a
property of the language you write it in.

Cost tracks effort rather than correctness. Go averaged $0.008338 a rollout
against Python's $0.006395, 1.30 times as much, with 9.58 agent steps against
6.62.

`expr-eval` reached this cohort through two pre-registered probes, both
published. The first passed 0 of 10, which its rule calls a wall rather than a
measurement, and the failure profile said why: no rollout ran out of steps or
context, every one wrote a working interpreter, and each failed only 1 to 6 of
15 cases with a different set each time. The fix was to give the agent a
feedback loop rather than to shrink the work, and it moved to 4 of 10.
See [docs/V10_REPORT.md](docs/V10_REPORT.md) and
[docs/EXPR_EVAL_PROBE.md](docs/EXPR_EVAL_PROBE.md).

## Roadmap

In priority order, each additive and accommodated by the current schema:

1. **More rungs on the within-language ladder**: the Python/typed-Python pair
   ships now; JavaScript with JSDoc and `checkJs`, and TypeScript non-strict,
   would turn the contrast into a dose–response curve.
2. **A second scaffold arm** through a real agent, per the section above.
3. **More task families**, per the power argument above. v0.9 shows the free
   gate is not enough on its own: `text-redact` passed calibration in all five
   languages and saturated anyway. The ten-rollout difficulty probe on the target
   rung, before committing a matrix, now gates every new family and costs about
   $0.06.
4. **More seeds on the cells that moved.** v1.0 splits the matched
   JavaScript/TypeScript pair 7 of 8 against 3 of 8 on `expr-eval`, with the
   typed arm behind. v0.9 measured a single-seed swing of 4 runs out of 8 on a
   fixed cell, so that split needs seeds before it is a finding.
5. **A second model family**, ideally third-party contributed.
6. **Reasoning effort as a crossed factor**, which needs its own design rather
   than being a byproduct of the selection ladder.

## Repository layout

| Path | What is in it |
|---|---|
| `tasks/` | one directory per task family, five language versions each, plus the shared verifier |
| `studies/` | study, probe, and schedule JSON: what was going to be run, fixed before it ran |
| `calibration/` | one calibration receipt per family, the free gate that has to be green first |
| `analysis/` | the report generators, one per cohort |
| `docs/` | the published site, the written reports, and the aggregate JSON behind them |
| `scripts/` | the gates, the runner, and `publish_version.py` |

Publishing a cohort is one command, `python3 scripts/publish_version.py --report
--version v1.0`. It rebuilds the aggregate JSON and the written report from the
run ledger and then rewrites every part of the site derived from them. The same
script run with `--check` is part of `validate-pages.sh`, so a page that drifts
from its data fails the build.

## Results and contributions

Runs go under `results/<model>/<date>/<run-id>/{run.json,events.jsonl}`. A
submission is valid only with a green calibration report, exact Git revision,
container digest, pinned tool/agent/Pier/model versions and effort, a raw public
trajectory, token/cache/cost metadata, and all verifier cases. Add other models
as new result directories; never overwrite existing runs.

See [docs/DESIGN.md](docs/DESIGN.md) for the full experimental design, each
family's `EQUIVALENCE.md` for its audit, and `schemas/` for the record formats.
