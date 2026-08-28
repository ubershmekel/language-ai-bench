# Equivalence notes

All five variants use the same instruction bytes and the same language-neutral
black-box verifier. Each starter is a three-file program (`parse`, `redact`,
`main`) implementing the same shallow behavior: only literal rules, a scan that
advances one position at a time and so reports overlapping matches, no merging,
no `minLength`, no `policy`, and almost no validation. Every starter passes
exactly the same two verifier cases and fails the same ten, so the null-failure
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
| `overlapping-literal-matches` | `literal-non-overlapping` |
| `merge-drops-touching` | `astral-mask`, `merge-touching`, `strict-allows-touching` |
| `min-length-after-merge` | `min-length-drops-before-merge` |
| `strict-allows-overlap` | `strict-rejects-overlap`, `rejects-invalid` |

Deliberately absent is a sabotage that swaps code points for UTF-16 units or
bytes. It would be a no-op in Python and so could not be caught by the same case
ids everywhere, which is exactly what the parity gate forbids. The code point
hazard is a hazard for the agent to fall into, not a fault the gate injects.

## What happened when it was run

v0.9 ran this family 8 times in each of the five languages. It passed 39 of 40,
and across those 40 runs not one failed `code-point-offsets` or `astral-mask`,
the two cases that catch offsets counted in UTF-16 code units or bytes. The
mechanism above is sound, but this task does not test it, because the
instruction gives the code point rule a paragraph of its own and adds that it
does not matter how your language indexes a string. That warning sits directly
on the hazard, so every arm converted to a code point array before writing any
logic.

The family is kept as it stands so the v0.9 result stays reproducible. A
revision that gives the rule one plain sentence, keeps the developer tests
ASCII only, and leaves every astral case hidden would test the mechanism
properly. It would need its own calibration run and its own cohort, and it
should not reuse this family's id.
