# Equivalence audit: optimistic concurrency

Equal LOC and forced file layouts are explicitly not goals. Values below are
behavioral/conceptual; discrepancies are recorded rather than normalized away.

| Dimension | JavaScript | TypeScript | Python | Go | Accepted discrepancy |
|---|---|---|---|---|---|
| Required behavior | 7 shared HTTP cases | same | same | same | none |
| Concepts | routing, handler, state, precondition, atomic update | same + static types | same + lock | same + compiler/mutex | language-native feedback is treatment |
| Baseline modules | one service module | one service module | one service module | one package | idiomatic tiny service |
| Call depth | request → handler → map | same | request → handler → dict | request → handler → map | effectively equal |
| Persistence | process-lifetime in-memory resource | same | same | same | durable DB deferred equally |
| Concurrency | event loop; compare immediately before commit | same | threaded server + lock | goroutines + mutex | native runtime models retained |
| Error surface | JSON/HTTP status | same | same | same | framework wording not graded |
| API boundary | HTTP `/tasks` | same | same | same | none |
| Visible tests | CRUD + stable ETag | same | same | same | same IDs/driver |
| Hidden tests | missing/stale tags, tag change, race, delete | same | same | same | none |
| Navigation | one implementation file plus scripts | same | same | same | TS adds config/lockfile |
| Unfamiliar code | small CRUD service | same JS lineage with annotations | independent stdlib server | independent stdlib server | ecosystems remain a named confound |

JS was authored as type-erased TS plus CommonJS/idiomatic cleanup; their
committed diff is reviewable with:

```sh
git diff --no-index tasks/optimistic-concurrency/javascript/src/server.js \
  tasks/optimistic-concurrency/typescript/src/server.ts
```

The agent sees `instruction.md` and developer cases `regression-crud` and
`etag-stable`. Hidden cases are `if-match-required`, `matching-tag-changes`,
`stale-write`, `concurrent-conflict`, and `deleted-stale`. The verifier observes
only HTTP behavior; it names no internal symbol and inspects no AST.

