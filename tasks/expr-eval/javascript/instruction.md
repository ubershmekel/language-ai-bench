# Finish the expression evaluator

`SPEC.md` in the project root is the contract. The code in `src/` implements a
small fraction of it: decimal literals, `+` and `*` with no precedence between
them, no bindings, and no error reporting. Make it satisfy the spec.

Do not add runtime dependencies or change the stdin/stdout interface.
`scripts/verify-local` runs the developer tests, most of which fail today.
