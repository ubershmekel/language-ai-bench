# Language AI Bench

A minimal, MIT-licensed experiment asking whether language and tooling feedback
change coding-agent success on the *same* software-engineering ticket. v0.1 has
one optimistic-concurrency task family and exactly four cells:

| Language | `typecheck_config` | Feedback |
|---|---|---|
| JavaScript | `none` | none |
| TypeScript | `strict` | structural, thorough |
| Python | `none` | none |
| Go | `default` | compiler, blocking |

**Do not read this as a four-language leaderboard.** JS/TS is the matched
centerpiece. Python and Go differ in ecosystem, diagnostics, compilation,
test-loop latency, and likely pretraining exposure. With one task family, v1 can
support no conclusion about languages in general. Anyone reading a language
ranking off this prototype is misreading it. Success means a fair pipeline and a green calibration report.

## Decision study: new versus existing Node projects

v0.3 adds a focused decision study for choosing JavaScript or strict TypeScript
when vibe coding. The original optimistic-concurrency family is the brownfield
condition: the agent changes an existing CRUD service. `task-service-greenfield`
is the greenfield condition: the agent receives a minimal runnable Node scaffold
and builds the same observable service contract. Each condition compares only
JavaScript with TypeScript, using identical runtime versions, task wording,
verifier bytes, model, effort, and bash-only scaffold.

The staged cells and stopping budget are recorded in `decision_benchmark.json`.
Results cover two related behavioral contracts but remain exploratory—not a
universal language ranking. Greenfield and brownfield pass rates are reported
separately. The current findings are in [`docs/DECISION_REPORT.md`](docs/DECISION_REPORT.md).

## Run it on Linux (or Docker Desktop's Linux engine)

Requirements: Docker and Python 3.11+. No language toolchains are needed on the
host. Base-image digests resolved during calibration are recorded in
`images.lock.json`; published runs must put their built image digest in
`run.json`.

```sh
git clone <this-repository>
cd language-ai-bench
sh scripts/run-local.sh
```

That command builds and behaviorally exercises all four real implementations,
runs reference/null/sabotage calibration, creates passing and failing zero-cost
mock rollouts, and prints per-cell aggregation. The checked-in
`calibration_report.json` is green. Direct commands:

```sh
python3 scripts/calibrate.py
python3 scripts/run_benchmark.py --agent mock-solve --seeds 2 \
  --max-spend-usd 10 --dry-run
python3 scripts/run_benchmark.py --agent mock-solve \
  --max-spend-usd 10 --acknowledge-projection
python3 analysis/feedback_to_fix.py path/to/events.jsonl
python3 analysis/aggregate.py results
```

`scripts/verify-local` in every variant starts the service, readiness-probes,
tests, and tears down in one shell invocation. This resolves mini-swe-agent's
non-persistent-shell asymmetry; the HTTP task was retained because its
observable state/concurrency contract is scientifically stronger than the CLI
fallback.

## Real agents through Pier

For secret setup, the two-rollout cost pilot, and the publication boundary, follow [the paid-run guide](docs/RUNNING_PAID.md).

Install [Pier](https://github.com/datacurve-ai/pier), then run one Harbor task
directory with a fresh context per seed:

```sh
uv tool install datacurve-pier
pier run -p tasks/optimistic-concurrency/typescript \
  --agent mini-swe-agent --model YOUR_PROVIDER/YOUR_MODEL
```

Pier—not this repository—owns sandboxing, model calls, network allowlists,
timeouts, and trajectories. Its current command surface should be checked with
`pier run --help`; this artifact intentionally does not wrap or reimplement it.
The mock runner proves schemas and controls locally but does not claim to be a
Pier execution. Import Pier's ATIF events into `events.jsonl`, retaining raw
fields, and populate the required `run.json` fields before analysis.

## Spend gate

Use a dedicated experiment-only API key with a provider-side hard limit equal
to planned spend plus a small margin. Never use a personal/shared key. The
provider cap is the only control that survives concurrent sandboxes or a runner
crash.

The projection is:

```text
rollout = sum(step_prefix_tokens × effective_input_rate)
        + output_tokens × output_rate
matrix  = rollout × 4 languages × seeds × task_families
```

The two-rollout cost pilot averaged `$0.00586597`. The balanced primary study
completed 22 runs for `$0.11832375`; every run reported token/cache/cost metadata.
`cost_pilot.json` stores the pilot. Provider spend remains the hard backstop,
with Pier runs serialized and a native `$0.10` per-rollout agent cost limit.

## Results and contributions

Runs go under `results/<model>/<date>/<run-id>/{run.json,events.jsonl}`. A
submission is valid only with a green calibration report, exact Git revision,
container digest, pinned tool/agent/Pier/model versions and effort, raw public
trajectory, token/cache/cost metadata, and all verifier cases. Add other models
as new result directories; do not overwrite existing runs. See
`docs/DESIGN.md`, `tasks/optimistic-concurrency/EQUIVALENCE.md`, and the schemas.

## Current status

- All original and decision-study task variants build and run in Linux containers.
- Reference 100%, null parity, and four-sabotage parity are green.
- Passing and plausible-failing mock runs exist with non-empty events.
- The balanced paid JS/TS study completed 22/22 with no exceptions; pass-rate cells hit a ceiling.
- TypeScript used modestly fewer output tokens/steps but longer agent wall time; see the decision report.
- DeepSWE's public corpus pilot remains incomplete because some published
  trajectory URLs are currently inaccessible (a [documented 403 issue](https://github.com/datacurve-ai/deep-swe/issues/59)); it cannot substitute for this matched family anyway.
