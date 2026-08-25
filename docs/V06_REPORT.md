# Language AI Bench v0.6: prospective clean polyglot study

## Bottom line

**All 36 prospective attempts passed the hidden verifier.** The observed correctness contrast is therefore zero for every language pair; this does not prove equal underlying success rates.

The primary efficiency estimand is the paired difference in agent steps within nine matched task-family × attempt blocks. Estimates below are prospective v0.6 only. Earlier results remain historical and are never pooled into these efficiency estimates.

## Prospective results

| Language | Passed | Mean steps | Mean output tokens | Mean agent time | Mean cost | Mean files changed | Mean +lines | Mean -lines |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| JavaScript | 9/9 | 6.89 | 2091 | 29.26s | $0.005318 | 2.00 | 46.6 | 8.3 |
| TypeScript | 9/9 | 6.44 | 2078 | 37.57s | $0.005328 | 4.33 | 172.0 | 8.8 |
| Python | 9/9 | 6.22 | 2091 | 26.84s | $0.004990 | 2.00 | 51.3 | 42.0 |
| Go | 9/9 | 6.89 | 2288 | 37.49s | $0.005588 | 2.11 | 47.1 | 5.9 |

## Paired primary comparisons

Differences are left minus right. The 95% intervals are percentile intervals from a fixed-seed 20,000-resample paired bootstrap over the nine complete task-family × attempt blocks.

| Contrast | Correctness difference (95% CI) | Agent-step difference (95% CI) |
|---|---:|---:|
| JavaScript − TypeScript | 0.000 [0.000, 0.000] | 0.44 [-0.33, 1.22] |
| JavaScript − Python | 0.000 [0.000, 0.000] | 0.67 [-0.11, 1.22] |
| JavaScript − Go | 0.000 [0.000, 0.000] | 0.00 [-1.00, 1.00] |
| TypeScript − Python | 0.000 [0.000, 0.000] | 0.22 [-0.44, 0.89] |
| TypeScript − Go | 0.000 [0.000, 0.000] | -0.44 [-1.78, 0.67] |
| Python − Go | 0.000 [0.000, 0.000] | -0.67 [-1.78, 0.44] |

All observed correctness differences and bootstrap intervals are exactly zero because every run passed. With only nine blocks, continuous-outcome intervals are necessarily broad and should be read as uncertainty descriptions, not rank certificates.

## Workflow and patch metrics

| Language | First explicit verification passed | Verified before submit | Mean verification attempts | Static-check invocations | Malformed actions | Dependency-manifest changes | Mean final workspace size |
|---|---:|---:|---:|---:|---:|---:|---:|
| JavaScript | 6/9 | 9/9 | 2.11 | 0 | 0 | 0 | 7.0 files / 11054 B |
| TypeScript | 6/9 | 6/9 | 2.33 | 0 | 0 | 0 | 11.7 files / 18242 B |
| Python | 9/9 | 9/9 | 2.33 | 0 | 0 | 0 | 5.7 files / 10742 B |
| Go | 6/9 | 7/9 | 2.11 | 13 | 0 | 0 | 6.7 files / 11054 B |

Patch counts compare each retained final workspace byte-for-byte with its committed task `environment/` baseline. Text line additions/deletions use UTF-8 line diffs; final workspace metrics exclude dependency/cache directories. No independent patch-review instrument was run, so review findings are reported as unavailable rather than inferred.

## Task topology

Implementation topology counts files and bytes under the committed baseline `src/` directory; workspace topology counts all committed environment files and bytes before the agent runs.

| Task family | Language | Source files | Source bytes | Workspace files | Workspace bytes |
|---|---|---:|---:|---:|---:|
| configuration-merge | Go | 1 | 1259 | 6 | 7342 |
| configuration-merge | JavaScript | 1 | 868 | 5 | 6852 |
| configuration-merge | Python | 1 | 626 | 5 | 6515 |
| configuration-merge | TypeScript | 1 | 1111 | 8 | 9127 |
| optimistic-concurrency | Go | 1 | 2070 | 7 | 4784 |
| optimistic-concurrency | JavaScript | 1 | 2094 | 7 | 4670 |
| optimistic-concurrency | Python | 1 | 2436 | 6 | 4815 |
| optimistic-concurrency | TypeScript | 1 | 2286 | 9 | 6712 |
| schedule-variants | Go | 1 | 3815 | 7 | 11595 |
| schedule-variants | JavaScript | 3 | 4109 | 9 | 11754 |
| schedule-variants | Python | 1 | 4908 | 6 | 12353 |
| schedule-variants | TypeScript | 4 | 4790 | 12 | 14303 |

Topology is part of the treatment bundle. Differences mediated by file layout, starter size, compiler/toolchain, or ecosystem must not be interpreted as syntax-only language effects.

## Infrastructure, spend, and scope

No infrastructure failures occurred in the prospective v0.6 cohort. The 36 prospective trials cost **$0.19101201** in measured provider spend; the maximum single-trial cap and the $0.75 study ceiling were never approached.

This study covers one model snapshot, one low-effort bash-only agent scaffold, three calibrated brownfield backend task families, four languages, and three attempts per cell. The randomized schedule was fixed before launch and executed serially without reordering.

**Historical boundary:** Earlier v0.4/v0.5 results remain published as historical evidence; their efficiency estimates are not pooled with prospective v0.6 estimates.

Machine-readable aggregates, including secondary paired intervals for cost, output tokens, agent time, and patch size, are in `data/v06-results.json`. The older report remains at `POLYGLOT_REPORT.md`.
