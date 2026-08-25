# Repair layered configuration merging

The supplied project contains a command-line JSON configuration merger. It reads
one JSON value from standard input and writes the merged configuration as JSON
to standard output.

The input must be an object containing exactly these four object-valued layers,
applied from lowest to highest precedence:

- `defaults`
- `file`
- `env`
- `cli`

Repair the existing implementation so that nested objects merge recursively.
Arrays and scalar values replace the lower-precedence value. A `null` value
deletes that key at its current object path; deletion of a missing key is a
no-op, and a later layer may add the key again. Inputs must not be mutated.

Reject malformed JSON, non-object input, missing or extra layers, or a layer
that is not an object by exiting nonzero. A successful invocation must emit only
the merged JSON value and exit zero.

Do not add runtime dependencies or change the stdin/stdout interface. Run
`scripts/verify-local` for developer tests. Hidden tests cover nested
precedence, deletion and re-addition, array replacement, type transitions,
invalid inputs, and flat-merge regressions.
