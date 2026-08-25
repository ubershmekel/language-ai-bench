# Equivalence notes

All four tasks use the same instruction bytes and the same language-neutral
black-box verifier. Each starter is a four-file program (`money`, `fx`,
`rollup`, `main`) implementing the same shallow behavior: floating-point
conversion, direct rates only, leaf-account totals, and almost no validation.
Every starter passes exactly the same four verifier cases and fails the same
eight, so the null-failure set is identical across languages.

Reference implementations use identical semantics: exact rational arithmetic
over arbitrary-precision integers, breadth-first shortest-path conversion with
ambiguity rejection, half-to-even rounding per entry, ancestor prefix rollup,
code-point ordering, and the same rejection set. Python uses `fractions`,
JavaScript and TypeScript use `BigInt` numerator/denominator pairs, and Go uses
`math/big.Rat`; all three are exact, so no language is forced into a different
algorithm.

This family is deliberately harder than the v0.6 families, which every language
solved on every attempt. It is a brownfield refactor whose central change — the
move from binary floating point to exact arithmetic — crosses all four files and
changes the type flowing between them, which is where static typing and compiler
feedback would be expected to matter if they matter anywhere.

No runtime dependency is required in any language. JavaScript and Python run
directly; TypeScript is compiled with the pinned compiler already used by this
benchmark; Go is built with the pinned Go image already used by this benchmark.
