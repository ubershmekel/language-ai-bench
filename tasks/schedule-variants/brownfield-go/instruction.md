# Add interval schedules to the job service

The service currently supports jobs with one-time schedules. Extend the existing
multi-file implementation so every job schedule is exactly one of:

- `{"kind":"once","at":"<ISO-8601 instant>"}`
- `{"kind":"interval","startAt":"<ISO-8601 instant>","everyMinutes":<positive integer>}`

Preserve existing `GET /jobs/:id`, `POST /jobs`, and `PATCH /jobs/:id` behavior.
`PATCH` replaces the complete schedule when `schedule` is supplied; switching
kinds must not retain fields from the old variant. Invalid requests return `400`
and must not mutate stored state. Missing jobs return `404`.

`GET /jobs/:id/next?after=<ISO-8601 instant>` returns `{"nextRun": ...}`. The
result is the first occurrence strictly after `after`, or `null` for an expired
one-time schedule. Return canonical UTC timestamps. Reject mixed, missing,
unknown, fractional, non-positive, or invalid schedule fields.

Run `scripts/verify-local` for developer tests. Hidden tests exercise variant
validation, kind switches, atomic failure, boundaries, and regressions.
