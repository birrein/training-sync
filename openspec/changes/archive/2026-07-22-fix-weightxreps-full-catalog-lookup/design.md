## Context

Training Sync uses a configured Weight x Reps user id to request the complete remote exercise catalog during synchronization preflight. The client currently declares the GraphQL `$uid` variable as `Int!`, while the remote API schema requires `ID!`, and selects `id` and `name` directly from `ExerciseStat` even though those fields are nested under `e`. Either mismatch makes the request fail with HTTP 400 before exercise resolution. The stored configuration remains numeric and must not be migrated or rewritten.

## Goals / Non-Goals

**Goals:**

- Restore complete-catalog lookup for a configured Weight x Reps user id.
- Preserve the existing full-catalog resolution and stop-before-write behavior.
- Add focused regression coverage for the remote query contract and parsed catalog result.

**Non-Goals:**

- Change the CLI, configuration paths, or stored user-id representation.
- Add fallback writes when complete-catalog lookup fails.
- Refactor authentication, exercise resolution, or JEditor persistence.
- Modify any Garmin activity, vault note, or Weight x Reps training day during verification.

## Decisions

- Declare the exercise-catalog GraphQL variable as `ID!`, matching the remote schema. GraphQL ID inputs accept the existing numeric variable value, so configuration parsing remains unchanged.
- Select `e { id name }` from each returned `ExerciseStat` and parse the nested exercise object into the existing name-to-id mapping.
- Keep `exercise_catalog(user_id)` and its integer-facing call sites stable. Widening application types or converting the configured value to a string would add unnecessary surface area without changing the remote contract.
- Test the exact query declaration, variables, and nested response shape through the mocked Weight x Reps client request. This catches either integration-contract regression before any live request.
- Verify the production credentials only with a read-only `exercise_catalog()` call. Synchronization writes are outside this change's verification scope.

## Risks / Trade-offs

- **Risk:** The remote schema changes again. **Mitigation:** A focused request-contract test identifies local drift, while a read-only live check validates the current integration.
- **Risk:** A broad fallback hides catalog lookup failures and weakens preflight. **Mitigation:** Keep failures explicit and preserve the existing no-write behavior.
- **Trade-off:** The test couples to the external scalar and response shape. This is intentional because both mismatches caused the production failure and are part of the integration boundary.
