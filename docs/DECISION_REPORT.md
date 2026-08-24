# JavaScript vs TypeScript for vibe-coded Node projects

## Bottom line

**Use TypeScript by default for projects you expect to keep or extend; use JavaScript for genuinely disposable scripts and tiny prototypes.**

That recommendation is not based on a pass-rate win: all 22 balanced runs passed. Under GPT-5.6 Luna at low reasoning effort, both languages solved both greenfield and brownfield tasks, including the harder cross-file schedule-union change. TypeScript showed no completion penalty and used modestly fewer output tokens and agent steps, but its compile/test loop took longer wall-clock time. The practical recommendation therefore combines this no-penalty result with the unmeasured maintenance value of static checks; it is not proof that TypeScript makes agents more accurate.

## Results by project maturity

| Condition | Language | Passed | Pass rate | Mean cost | Mean output | Mean steps | Mean agent time |
|---|---|---:|---:|---:|---:|---:|---:|
| Brownfield | JavaScript | 5/5 | 100% | $0.005514 | 2302 | 7.00 | 33.66s |
| Brownfield | TypeScript | 5/5 | 100% | $0.005496 | 2132 | 6.60 | 49.13s |
| Greenfield | JavaScript | 6/6 | 100% | $0.005335 | 2543 | 6.50 | 35.81s |
| Greenfield | TypeScript | 6/6 | 100% | $0.005211 | 2430 | 5.83 | 45.13s |

Descriptive TypeScript-versus-JavaScript differences:

- **Brownfield:** pass-rate difference 0 points; output tokens -7.39%, steps -5.71%, cost -0.32%, agent time +45.96%.
- **Greenfield:** pass-rate difference 0 points; output tokens -4.46%, steps -10.31%, cost -2.32%, agent time +26.03%.

## What the result licenses

- For these two Node/HTTP contracts, this model/scaffold completed JavaScript and strict TypeScript equally often.
- TypeScript did not make greenfield generation less likely to succeed and did not obstruct brownfield schema evolution.
- The small efficiency differences are descriptive; with 5 brownfield and 6 greenfield runs per language, they are not stable population estimates.

## What it does not license

Every cell reached 100%, so the study cannot estimate a TypeScript accuracy advantage or establish equivalence. The 95% Wilson lower bound is only about 57% for 5/5 and 61% for 6/6. This is one model snapshot, low effort, a bash-only agent, two related backend contracts, and no LSP/editor feedback. It does not test React/Next.js ecosystems, long-lived maintenance, human review, dependency migrations, or defect rates after future changes.

## Practical choice

- **New application expected to grow:** TypeScript. The agent paid no observed success penalty, and future edits gain compiler feedback.
- **Existing multi-file application:** TypeScript, more strongly. Cross-module schema changes are exactly where static contracts provide insurance, even though this model solved both arms.
- **One-off automation, throwaway prototype, or tiny script:** JavaScript is reasonable when minimizing setup and compile latency matters more than future refactors.

Primary paid spend was **$0.11832375**. Raw Pier jobs remain private; the public JSON contains aggregates only.

See [`data/decision-results.json`](data/decision-results.json) for machine-readable aggregates and confidence intervals.
