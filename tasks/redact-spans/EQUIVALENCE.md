# Equivalence notes

All five variants use the same instruction bytes and the same language-neutral
black-box verifier. Each starter is a three-file program (`parse`, `redact`,
`main`) implementing the same shallow behavior: only literal rules, a scan that
advances one position at a time and so reports overlapping matches, no merging,
no `minLength`, no `policy`, and almost no validation. Every starter passes
exactly the same two verifier cases and fails the same eleven, so the null-failure
set is identical across languages.

Reference implementations use identical semantics: code point offsets, the
`minLength` drop applied to each rule's own spans before merging, merging of
spans that overlap or touch, the strict policy rejecting overlaps but not
touches, per-rule match counts in input order, and the same rejection set. No
language is forced into a different algorithm.

## Why this family exists

`money-rollup` and `circuit-breaker` rank the arms in nearly opposite orders,
and both orderings follow from the affordance each task rewards. `money-rollup`
rewards having exact rational arithmetic in the standard library, which Python
has. `circuit-breaker` rewards not dropping a case of a union that crosses
module boundaries, which `tsc`, `go build`, and `mypy` all report. Neither
result generalizes on its own, and a third family that repeated either mechanism
would not break the tie.

This family routes difficulty through a third thing: **what a string is at
runtime**. Every offset and length in the contract counts Unicode code points.
Python indexes code points already, so it needs no conversion. JavaScript
indexes UTF-16 code units, so an astral character counts as two unless the code
converts. Go indexes bytes, so the same character counts as four. TypeScript
inherits JavaScript's representation exactly, and `tsc` reports nothing about
it, because `string` is `string` whichever unit you meant.

Go is the interesting arm here. Its compiler does not know the contract, but it
does force `string` and `[]rune` apart at every boundary, so the decision is
made in the open rather than by accident. The three type-checked arms therefore
split on this family in a way they did not on `circuit-breaker`, where all three
checkers reported the same missing case. That split is the reason to run it.

The other difficulty is specification breadth, as in the other two families:
two rule kinds, a length filter whose position in the pipeline is observable, a
merge rule that treats touching and overlapping spans the same way, a policy
that treats them differently, per-rule statistics that count spans after the
filter, and a wide rejection surface.

## Topology

The three-file split is the same in every language. Topology still differs:
TypeScript compiles, Go builds a binary, `python-typed` runs `mypy --strict` in
its developer loop, and JavaScript and Python run directly. Those differences
are part of the treatment bundle and are recorded rather than normalized away.

No runtime dependency is required in any language. There is no clock, no
randomness, and no filesystem or network access: the whole run is a pure
function of one JSON document, so the verifier is deterministic.

## Sabotages

The four calibration sabotages are all logic-level, so each is expressible the
same way in all five languages and is caught by the same case ids everywhere:

| Sabotage | Caught by |
|---|---|
| `overlapping-literal-matches` | `literal-non-overlapping`, `astral-literal-scan` |
| `merge-drops-touching` | `astral-mask`, `merge-touching`, `strict-allows-touching` |
| `min-length-after-merge` | `min-length-drops-before-merge` |
| `strict-allows-overlap` | `strict-rejects-overlap`, `rejects-invalid` |

Deliberately absent is a sabotage that swaps code points for UTF-16 units or
bytes. It would be a no-op in Python and so could not be caught by the same case
ids everywhere, which is exactly what the parity gate forbids. The code point
hazard is a hazard for the agent to fall into, not a fault the gate injects.

## Where this family came from

`redact-spans` is `text-redact` with the hazard no longer announced. That family
ran 8 times in each of the five languages in v0.9, passed 39 of 40, and across
those 40 runs not one failed `code-point-offsets` or `astral-mask`, the two
cases that catch offsets counted in UTF-16 code units or bytes. The mechanism
was sound and the task did not test it: the instruction titled itself after the
hazard, gave the code point rule a paragraph of its own ending in a sentence
saying it does not matter how your language indexes a string, and closed by
naming the two hidden cases. Every language converted to a code point sequence
before writing any logic.

Three things changed here, and nothing else:

1. The instruction states the unit once, where each field is defined. The title,
   the dedicated paragraph, and the list of hidden cases are gone.
2. `astral-literal-scan` is a new hidden case whose literal is itself an astral
   string, so the non-overlapping scan has to advance by code points.
3. `merge-touching` and `min-length-drops-before-merge` run over astral text.

Measured, not assumed: take the JavaScript reference and change its one code
point conversion to `text.split("")`, which is the mistake this family exists to
catch, and it fails seven of the thirteen cases here against four of twelve
under `text-redact`. The developer tests remain ASCII only, which is what leaves
the hidden cases something to catch.

`text-redact` is left in the tree unmodified so the v0.9 cohort stays
reproducible. The two families must never be pooled or compared as one: they
have different instructions and different hidden cases, so a pass rate under one
id says nothing about the other.

The starter is the same one, and it fails eleven of the thirteen cases in every
language.

## Status: not admitted

Ten paid rollouts, two per language, at the same rung the cohorts use, with the
admission rule written down first. All ten passed and none failed a wrong-unit
case, so the family is not admitted to a cohort. The de-signposting was not the
binding constraint: at this rung the model counts code points correctly in every
language without being told to. See `docs/REDACT_SPANS_PROBE.md` for the
receipt. The family stays in the tree with its gate green because it is the
evidence for that claim, and because a larger version of the same contract is
the next thing worth trying.
