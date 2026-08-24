# Equivalence audit: greenfield task service

This family represents a new project created from a minimal runnable Node
scaffold. It is analyzed separately from the brownfield optimistic-concurrency
family; pass rates must never be pooled across maturity conditions.

| Dimension | JavaScript | TypeScript | Accepted discrepancy |
|---|---|---|---|
| Runtime/base image | Node 22.14, pinned digest | same | none |
| Package ecosystem | npm, no runtime dependencies | npm plus pinned compiler/types | static feedback is the treatment |
| Starter behavior | seeded readiness endpoint; all other routes return 501 | type-annotated/type-erased equivalent | annotations and build step only |
| Required contract | seven shared HTTP verifier cases | same | none |
| Visible tests | CRUD regression + stable ETag | same verifier bytes | none |
| Hidden tests | preconditions, tag changes, race, deletion | same verifier bytes | none |
| Agent interface | mini-swe-agent bash-only | same | none |
| Local command | `scripts/verify-local` | same intent plus `tsc` | compiler feedback is the treatment |

The TypeScript starter is the JavaScript starter with imports/type context and
strict compilation; the behavioral scaffold is otherwise matched. The shared
reference solutions and verifier are inherited from the brownfield family so
only the starting-code condition changes.
