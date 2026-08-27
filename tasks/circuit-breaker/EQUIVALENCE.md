# Equivalence notes

All five variants use the same instruction bytes and the same language-neutral
black-box verifier. Each starter is a three-file program (`parse`, `breaker`,
`main`) implementing the same shallow behavior: one global breaker instead of
one per target, no cooldown, no half-open probing, every non-success outcome
counted as a failure, and almost no validation. Every starter passes exactly the
same three verifier cases and fails the same nine, so the null-failure set is
identical across languages.

Reference implementations use identical semantics: per-target breakers, a
three-state machine with cooldown-driven half-open probing, a three-way outcome
classification in which an unlisted status is neutral rather than a success, and
the same rejection set. No language is forced into a different algorithm; the
state machine and the outcome union are expressible directly in all five.

This family exists because the v0.7 failure table showed `money-rollup`
discriminating on numeric semantics and specification breadth rather than on
anything a type checker sees. Its difficulty is deliberately routed through
shapes that cross module boundaries: a three-state union and a three-variant
outcome union, both consumed in more than one file, where a missed case is
silent in JavaScript and Python and visible to `tsc`, `go build`, and `mypy`.
The lever is specification breadth, not algorithmic trickiness, following the
DeepSWE observation that its hardest tasks combine many interacting rules rather
than one hard algorithm.

The three-file split is the same in every language. Topology still differs:
TypeScript compiles, Go builds a binary, `python-typed` runs `mypy --strict` in
its developer loop, and JavaScript and Python run directly. Those differences
are part of the treatment bundle and are recorded rather than normalized away.

No runtime dependency is required in any language. The clock is supplied in the
input as an explicit `at` timestamp on every call, so no variant sleeps, polls,
or reads the wall clock, and the verifier is deterministic.
