# Build a job service with schedule variants

Build the HTTP service in the supplied Node project. It must listen on
`0.0.0.0` at `PORT` (default `8080`) and store jobs in memory. Start with job
`1`, named `backup`, scheduled once at `2030-01-01T00:00:00.000Z`.

Every job schedule is exactly one of:

- `{"kind":"once","at":"<ISO-8601 instant>"}`
- `{"kind":"interval","startAt":"<ISO-8601 instant>","everyMinutes":<positive integer>}`

Implement `GET /jobs/:id`, `POST /jobs`, `PATCH /jobs/:id`, and
`GET /jobs/:id/next?after=<ISO-8601 instant>`. `PATCH` replaces the complete
schedule when supplied; switching kinds must not retain old fields. Invalid
requests return `400` without mutation, and missing jobs return `404`.

The next-run result is the first occurrence strictly after `after`, or `null`
for an expired one-time schedule. Return canonical UTC timestamps. Reject mixed,
missing, unknown, fractional, non-positive, or invalid schedule fields.

Run `scripts/verify-local` for developer tests. Hidden tests exercise variant
validation, kind switches, atomic failure, boundaries, and regressions.
