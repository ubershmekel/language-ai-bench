# Expression evaluator

The program reads one JSON object from standard input and writes one JSON
object to standard output.

## Input

```json
{"config": {"maxDepth": 8},
 "programs": [{"id": "p1", "source": "let x = 6; x * 7"}]}
```

## Output

```json
{"results": [{"id": "p1", "value": 42}], "stats": {"programs": 1, "failed": 0}}
```

`results` follows input order. A program that fails yields
`{"id": ..., "error": {"code": ..., "at": ...}}` instead of `value`, where `at`
is an offset into `source` counted in Unicode code points. `stats.failed`
counts those. Every `value` is emitted as an exact JSON integer.

## Grammar

```
program        := ("let" IDENT "=" expr ";")* expr
expr           := bitor
bitor          := bitxor ("|" bitxor)*
bitxor         := bitand ("^" bitand)*
bitand         := equality ("&" equality)*
equality       := relational (("==" | "!=") relational)*
relational     := shift (("<" | "<=" | ">" | ">=") shift)*
shift          := additive (("<<" | ">>") additive)*
additive       := multiplicative (("+" | "-") multiplicative)*
multiplicative := unary (("*" | "/" | "%") unary)*
unary          := ("-" | "~") unary | primary
primary        := INT | IDENT | "(" expr ")"
```

Every binary operator is left-associative. `INT` is `[0-9]+` or `0x` followed by
one or more hexadecimal digits, either case. `IDENT` is
`[A-Za-z_][A-Za-z0-9_]*`, except that `let` is a keyword. Space, tab, carriage
return, and newline separate tokens and are otherwise ignored.

## Values

Every value is a signed 64-bit two's complement integer. Every operation
reduces its result modulo 2^64 into the range -2^63 through 2^63 - 1.

- `+`, `-`, `*` and unary `-` wrap.
- `/` truncates toward zero. `%` takes the sign of its left operand and
  satisfies `a == (a / b) * b + (a % b)`.
- `<<` wraps. `>>` propagates the sign bit.
- `&`, `|`, `^` and `~` operate on all 64 bits of the two's complement
  representation.
- The comparisons yield 1 for true and 0 for false, comparing as signed.
- A literal denotes a nonnegative integer no greater than 2^64 - 1. A literal
  of 2^63 or more denotes its two's complement reading, so `0x8000000000000000`
  is -9223372036854775808.

## Bindings

`let` bindings take effect in order, and a later binding shadows an earlier one
of the same name. The final expression is the program's result.

## Errors

A program yields at most one error. Parsing runs left to right and reports the
first problem it meets; if parsing succeeds, evaluation reports the first
problem it meets, evaluating the left operand of a binary operator before the
right and both before the operator itself.

| Code | Raised when | `at` |
|---|---|---|
| `PARSE` | a character that begins no token, or a token the grammar does not allow there, or input that ends early | the offending offset, or the code point count of `source` if the input ended early |
| `DEPTH` | an opening parenthesis nested deeper than `config.maxDepth` | that parenthesis |
| `LITERAL_RANGE` | a literal greater than 2^64 - 1 | the literal's first digit |
| `UNDEFINED` | an identifier with no binding in scope | the identifier |
| `DIVIDE_BY_ZERO` | the right operand of `/` or `%` is 0 | the operator |
| `SHIFT_RANGE` | the right operand of `<<` or `>>` is outside 0 through 63 | the operator |

## Rejection

Exit nonzero, writing nothing to standard output, for malformed JSON, a
non-object document, missing or extra top-level keys, a `config` that is not an
object, missing or extra config keys, a `maxDepth` that is not an integer of at
least 1, a `programs` value that is not an array, a program that is not an
object, missing or extra program keys, an `id` that does not match
`[A-Za-z0-9_.-]+`, a duplicate `id`, and a `source` that is not a string.
Booleans are not integers. A successful run writes only the result JSON and
exits zero.
