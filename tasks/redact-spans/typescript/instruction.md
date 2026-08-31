# Rework the redaction tool

The supplied project contains a command-line redaction tool. It reads one JSON
object from standard input and writes the result as JSON to standard output. The
current implementation understands only literal rules, scans for them one
position at a time, never merges the spans it finds, ignores most of the
configuration, and validates almost nothing. Rework it so it satisfies the
contract below.

## Input

```json
{
  "config": {"mask": "*", "policy": "merge", "minLength": 1},
  "text": "token abc secret abc end",
  "rules": [
    {"id": "r1", "kind": "literal", "value": "abc"},
    {"id": "r2", "kind": "span", "start": 10, "end": 16}
  ]
}
```

## Required behavior

**Rules.** A `literal` rule matches every non-overlapping occurrence of `value`,
scanning left to right and resuming immediately after each match it takes. A
`span` rule contributes the single half-open range `[start, end)`, whose bounds
are Unicode code point offsets into `text`. Each rule produces zero or more
spans.

**Minimum length.** A span shorter than `minLength` code points is dropped, and
this happens to each rule's own spans before any merging.

**Policy.** Under `"strict"`, exit nonzero if any two surviving spans overlap,
meaning they share at least one code point. Spans that merely touch, where one
ends at the code point the next begins, do not overlap. Under `"merge"`,
overlaps are allowed.

**Merging.** Surviving spans that overlap or touch become one output span
covering all of them. Its `rules` is the distinct set of contributing rule ids,
sorted ascending by Unicode code point. Output spans are sorted ascending by
`start`.

**Masking.** Every code point inside an output span is replaced by `mask`.

**Output.** `stats.rules` lists every rule in input order with the number of
spans it contributed after the `minLength` drop, including rules that
contributed none. `stats.codePoints` is the number of code points in `text` and
`redactedCodePoints` is the total length of the output spans.

For the input above:

```json
{"redacted":"token *** ****** *** end",
 "spans":[{"start":6,"end":9,"rules":["r1"]},{"start":10,"end":16,"rules":["r2"]},
          {"start":17,"end":20,"rules":["r1"]}],
 "stats":{"codePoints":24,"redactedCodePoints":12,
          "rules":[{"id":"r1","matches":2},{"id":"r2","matches":1}]}}
```

**Rejection.** Exit nonzero for malformed JSON, non-object input, missing or
extra top-level keys, a `text` that is not a string, a `config` or `rules` value
of the wrong type, missing or extra config keys, a `mask` that is not a string
of exactly one code point, a `policy` other than `merge` or `strict`, a
`minLength` that is not an integer of at least one, a rule that is not an
object, an unknown rule `kind`, missing or extra keys for the kind in use, an
`id` that does not match `[A-Za-z0-9_.-]+`, a duplicate `id`, a `value` that is
not a nonempty string, a `start` or `end` that is not a non-negative integer, a
`start` that is not less than its `end`, an `end` greater than the code point
count of `text`, and overlapping spans under the `strict` policy. A successful
run emits only the result JSON and exits zero.

Do not add runtime dependencies or change the stdin/stdout interface. Run
`scripts/verify-local` for developer tests. Hidden tests cover the whole
contract.
