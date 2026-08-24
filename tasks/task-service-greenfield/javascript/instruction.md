# Build a task service with optimistic concurrency

Build the HTTP service in `src/server.js` or `src/server.ts` using the supplied
Node project. It must listen on `0.0.0.0` at `PORT` (default `8080`) and provide
JSON CRUD endpoints at `/tasks` and `/tasks/:id`:

- Start with task `{"id":"1","title":"calibrate","done":false}`.
- `GET /tasks`, `POST /tasks`, and `GET /tasks/:id` preserve ordinary CRUD behavior.
- `GET /tasks/:id` responses include a stable quoted `ETag` derived from resource state.
- Existing-resource `PUT`, `PATCH`, and `DELETE` require `If-Match`; return `428` when absent and `412` when stale.
- A successful write changes the tag.
- Two writes using the same tag must not both succeed.
- A stale tag must not recreate or mutate a deleted resource.
- Return `404` for missing resources and `405` for unsupported methods.

Use the provided package configuration and standard-library APIs. Run
`scripts/verify-local` for developer tests. Hidden tests exercise errors,
concurrency, deletion, and CRUD regressions.
