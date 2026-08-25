# Equivalence audit: schedule variants

This family is the discriminating follow-up after the simpler task-service
contract reached a 100% pass ceiling. It models a realistic domain-schema
change: adding an interval variant beside an existing one-time schedule.

| Dimension | Brownfield JavaScript | Brownfield TypeScript | Greenfield JavaScript | Greenfield TypeScript |
|---|---|---|---|---|
| Runtime | Node 22.14 pinned digest | same | same | same |
| Starting behavior | multi-file once-only service | type-erased/annotated match | seeded readiness scaffold | annotated match |
| Required behavior | add interval union + preserve once | same | build both variants | same |
| Observable cases | seven shared HTTP cases | byte-identical verifier | same | same |
| Feedback | runtime/dev verifier | strict `tsc` + verifier | runtime/dev verifier | strict `tsc` + verifier |
| Agent/scaffold | mini-swe-agent bash-only | same | same | same |

Brownfield is a within-family schema-evolution comparison. The TypeScript
baseline declares `Schedule = OnceSchedule`; extending it to a discriminated
union forces the scheduler and storage boundaries to remain consistent.
JavaScript has the same modules and behavior without compiler diagnostics.

Greenfield starts from the same minimal runnable behavior in both languages.
Package/compiler metadata is intentionally part of the language treatment.
Pass rates are never pooled across maturity conditions or task families.
v0.5 adds brownfield Python and Go variants with the same prompt and byte-identical
HTTP verifier. Python uses its standard-library HTTP server without a static
checker; Go uses the pinned compiler. The four brownfield references, untouched
baselines, and four seeded sabotage modes have identical pass/failure sets in
`schedule_polyglot_calibration_report.json`.