# Equivalence notes

All five variants use the same instruction bytes, the same `SPEC.md` bytes, and
the same language-neutral black-box verifier. Each starter is a three-file
program (`parse`, `evaluate`, `main`) implementing the same shallow behavior:
decimal literals, `+` and `*` applied left to right with no precedence between
them, no bindings, no error reporting, and almost no validation. Every starter
passes exactly the same two verifier cases and fails the same thirteen, so the
null-failure set is identical across languages.

Reference implementations use identical semantics: the same precedence ladder,
the same left associativity, signed 64-bit two's complement values, truncating
division, sign-of-dividend remainder, arithmetic right shift, a checked shift
count, literals read as unsigned and reinterpreted as signed, and the same error
codes at the same offsets. No language is forced into a different algorithm.

## Why this family exists

The three older families each turn on one affordance: exact arithmetic in the
standard library (`money-rollup`), not dropping a case of a union that crosses
files (`circuit-breaker`), and what a string is at runtime (`text-redact`, which
saturated). This one turns on a fourth: **what an integer is**.

The contract is 64-bit two's complement, and no arm gets that for free in the
same way.

| Language | What it starts with | What it has to do |
|---|---|---|
| Go | `int64` wraps, `/` truncates, `>>` is arithmetic | almost nothing, but it must parse literals as `uint64` and reinterpret |
| Python | unbounded integers, `//` floors, `%` follows the divisor | wrap every result, and implement truncating division itself |
| Python (typed) | the same | the same; `mypy` reports none of it |
| JavaScript | `number` is a float64, bitwise operators are 32 bits | use `BigInt` everywhere and mask to 64 bits, and serialize without `JSON.stringify` |
| TypeScript | the same as JavaScript | the same; `tsc` does report `bigint` against `number`, and nothing else |

Two of those are silent traps rather than visible ones. `2 ** 53` is where a
JavaScript `number` stops being exact, and `1 << 40` in JavaScript is not
1099511627776. Neither is a type error in JavaScript, and only the second is
one in TypeScript. Python's `//` on a negative dividend disagrees with the
contract, and no checker anywhere reports that.

Go is the arm with the least to do, which is the opposite of `money-rollup` and
makes this family worth running next to it.

## Why the instruction is eight lines

Every other family in this repo states its whole contract in the instruction, at
69 to 82 lines. DeepSWE's median instruction is 15 lines over a real repository,
and its median reference patch is 844 lines against 301 here. The size ratio is
backwards, and v0.9 plus the `redact-spans` probe showed that hiding a hazard in
a small task does not make it hard.

So the contract lives in `SPEC.md` in the workspace, the ticket points at it,
and the work is bigger: the reference is a tokenizer, a precedence-climbing
parser, and an evaluator, against a starter that has none of those.

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
| `precedence-additive-first` | `precedence-table` |
| `truncate-toward-negative` | `division-truncation` |
| `shift-count-unchecked` | `shift-range` |
| `literal-range-unchecked` | `literal-range` |

Deliberately absent is a sabotage that drops the 64-bit reduction. It would be a
no-op in Go, whose `int64` wraps on its own, so it could not be caught by the
same case ids everywhere, which is what the parity gate forbids. The width of an
integer is a hazard for the agent to fall into, not a fault the gate injects.
