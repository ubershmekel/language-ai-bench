# Equivalence notes

All four tasks use the same instruction bytes and the same language-neutral
black-box verifier. Each starter implements the same intentionally shallow merge
and validates the same input envelope. Reference implementations use identical
recursive merge, deletion, array-replacement, and validation semantics.

The task is brownfield bug repair over one implementation file. No runtime
dependency is required in any language. JavaScript and Python run directly;
TypeScript is compiled with the pinned compiler already used by this benchmark;
Go is built with the pinned Go image already used by this benchmark.
