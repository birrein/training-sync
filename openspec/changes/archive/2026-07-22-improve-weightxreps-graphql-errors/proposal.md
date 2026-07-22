## Why

Weight x Reps can return useful GraphQL validation details in an HTTP 400 response, but the client currently raises the generic HTTP error before reading that payload. This hides the actual contract mismatch and makes synchronization failures unnecessarily difficult to diagnose.

## What Changes

- Parse Weight x Reps GraphQL response payloads before applying generic HTTP status handling.
- Surface GraphQL `errors` details for both successful and failed HTTP responses.
- Preserve the existing authentication refresh behavior and generic HTTP errors when no GraphQL error payload is available.
- Add regression coverage for an HTTP 400 response containing GraphQL validation errors.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `weightxreps-cardio-sync`: require actionable GraphQL error details when Weight x Reps rejects a request during synchronization.

## Impact

- `src/training_sync/weightxreps/client.py`: GraphQL response error ordering and diagnostics.
- `tests/test_weightxreps_client.py`: regression coverage for HTTP 400 GraphQL errors and existing fallback behavior.
- No CLI, configuration, dependency, credential, Garmin, vault, or Weight x Reps record changes.
