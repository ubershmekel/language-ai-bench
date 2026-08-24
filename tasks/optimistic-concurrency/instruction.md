# Add optimistic concurrency to tasks

The service already supports CRUD for `/tasks/:id`. Add HTTP optimistic
concurrency control:

- `GET` responses include a stable quoted `ETag` derived from resource state.
- Existing-resource `PUT`, `PATCH`, and `DELETE` require `If-Match`; return
  `428` when absent and `412` when stale.
- A successful write changes the tag.
- Two writes using the same tag must not both succeed.
- A stale tag must not recreate or mutate a deleted resource.

Preserve existing behavior. Run `scripts/verify-local` for the developer tests.
Hidden tests exercise errors, concurrency, deletion, and regressions.

