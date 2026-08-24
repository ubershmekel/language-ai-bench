# Running paid rollouts safely

## 1. Secret setup

From the repository root:

```sh
cp .env.example .env
chmod 600 .env
```

Edit `.env` to contain exactly:

```dotenv
OPENROUTER_API_KEY=<paste-your-key-here>
```

`.env`, Pier's `jobs/`, and `private-results/` are gitignored. Do not put the
key in a command, YAML file, screenshot, trajectory, issue, Actions secret
output, or committed results. Check before every push:

```sh
git check-ignore .env
git grep -n 'OPENROUTER_API_KEY=' -- . ':!.env.example' ':!docs/RUNNING_PAID.md'
```

The second command should print nothing. Rotate the key immediately if it ever
appears in Git history; deleting the working-tree line is not sufficient.

## 2. Install and free checks

Use Python 3.12+ and Docker's Linux engine:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install datacurve-pier==0.3.1
python scripts/calibrate.py
pier --version
pier run --help
```

On native Windows, Pier 0.3.1 writes its Linux Squid bootstrap script with
CRLF endings. Apply the pinned, idempotent workaround after installation:

```powershell
.\.venv\Scripts\python.exe scripts\patch_pier_windows.py
```

The script refuses to modify any other Pier version and is a no-op on Linux.

Calibration must remain green. Pier changes independently of this repository,
so record `pier --version` and pin that version before publishing a real batch.

## 3. Two-rollout cost pilot

Start with one language and one trial at a time, not the full matrix. Run the
command twice only after checking spend between runs. The model must use
the `openrouter/` prefix; this selects mini-swe-agent's native OpenRouter adapter
and preserves OpenRouter's upstream cost metadata.

```sh
pier run -p tasks/optimistic-concurrency/typescript \
  --agent mini-swe-agent \
  --model openrouter/openai/gpt-5.6-luna \
  --env-file .env \
  --agent-kwarg reasoning_effort=low \
  --agent-kwarg set_cache_control=default_end \
  --n-attempts 1 \
  --n-concurrent 1 \
  --sample-seed 20260824
```

This produces one attempt. Pier writes raw trials under `jobs/`, which is
private by default. Inspect the trajectory usage fields and measured upstream
cost; do not proceed if usage/cost/cache metadata is absent. After checking the
OpenRouter dashboard, repeat with `--sample-seed 20260825`. Replace the
mock-only values in `cost_pilot.json` with the two measured trials.

The OpenRouter $5/day cap is the provider backstop. Keep the experiment's
harness ceiling lower (recommended first-session ceiling: `$4.00`) so retries
and unrelated activity have margin. This repository's demonstrated
`--max-spend-usd` control currently applies only to the local mock pipeline;
it does **not** wrap Pier. Until a tested Pier usage importer/control is added,
run one Pier trial at a time and check the OpenRouter usage dashboard after each
trial. Do not launch the four-language matrix under the mistaken belief that
the mock runner limits Pier spending.

## 4. Full matrix gate

After the two-rollout pilot:

```sh
python scripts/run_benchmark.py --agent mock-solve --seeds 5 \
  --measured-cost-per-rollout-usd COST_FROM_PILOT \
  --max-spend-usd 4 --dry-run
```

Only acknowledge a projection below the remaining provider allowance. The
model-selection ladder comes before the full matrix. Keep model snapshot,
reasoning effort, mini-swe-agent version, Pier version, and system prompt fixed.

## 5. Publication boundary

`jobs/` and `private-results/` are raw/private. GitHub Pages consumes only
`docs/data/public-summary.json`, produced by:

```sh
python scripts/publish_results.py --results results \
  --output docs/data/public-summary.json
```

The exporter allowlists aggregate fields; it never copies events, prompts,
commands, environment variables, file contents, or trajectories. Review the
generated diff before committing. Raw public trajectories, if the research
release eventually requires them, should be a deliberate separately audited
artifact—not an automatic Pages input.
