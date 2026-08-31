# Make the money rollup report exact

The supplied project contains a command-line reporting tool. It reads one JSON
object from standard input and writes the report as JSON to standard output. The
current implementation converts with floating-point arithmetic, understands only
direct exchange rates, totals only the accounts named by entries, and validates
almost nothing. Rework it so it satisfies the contract below.

## Input

```json
{
  "reportCurrency": "USD",
  "currencies": {"USD": 2, "JPY": 0, "BHD": 3},
  "rates": [{"from": "JPY", "to": "USD", "rate": "0.0067"}],
  "entries": [{"account": "assets:cash", "currency": "JPY", "amount": "1250"}]
}
```

`currencies` maps a currency code to its number of minor-unit decimal places.
`rates` is a list of directed conversion edges. `entries` is a list of ledger
entries. `amount` and `rate` are decimal strings, never JSON numbers.

## Required behavior

**Exact arithmetic.** Every amount, rate, and product must be computed exactly.
No intermediate value may pass through binary floating point. Results must stay
exact for amounts far beyond 64-bit float precision, such as
`"123456789012345678"`.

**Amounts.** An `amount` matches `-?[0-9]+(\.[0-9]+)?` and carries at most as
many decimal places as its own currency allows. A `rate` matches
`[0-9]+(\.[0-9]+)?`, carries at most 8 decimal places, and is strictly positive.

**Conversion.** Convert each entry into `reportCurrency` by multiplying the
rates along the directed path of fewest edges from the entry currency to the
report currency. An entry already in the report currency uses a factor of one.
Exit nonzero if no directed path exists, or if two or more distinct paths tie
for fewest edges. Edges are one-way: a `JPY`->`USD` rate does not convert `USD`
to `JPY`.

**Rounding.** Round each converted entry to the report currency's minor units
using round-half-to-even, then total the rounded per-entry values. Do not round
totals afterwards.

**Rollup.** An account is a colon-separated path whose segments each match
`[A-Za-z0-9_]+`. Report every account and every ancestor prefix; each row totals
that account plus all of its descendants. Sort rows ascending by Unicode code
point. Format each total with exactly the report currency's decimal places, and
never emit a negative zero.

The example above reports `assets` and `assets:cash`, both `"8.38"`:

```json
{"reportCurrency":"USD","accounts":[{"account":"assets","total":"8.38"},{"account":"assets:cash","total":"8.38"}]}
```

**Rejection.** Exit nonzero for malformed JSON, non-object input, missing or
extra top-level keys, a `rates` or `entries` value that is not a list, missing
or extra entry or rate keys, a non-string amount or rate, a malformed amount,
rate, or account, an unknown currency code anywhere, an empty `currencies` map,
a minor-unit value that is not an integer in 0 through 4, a rate whose endpoints
are equal, and two rates sharing the same `from` and `to` pair.
A successful run emits only the report JSON and exits zero.

Do not add runtime dependencies or change the stdin/stdout interface. Run
`scripts/verify-local` for developer tests.
