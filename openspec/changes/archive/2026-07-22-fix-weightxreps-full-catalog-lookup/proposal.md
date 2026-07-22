## Why

When a configured Weight x Reps user id is available, Training Sync attempts to load the complete exercise catalog before resolving exercises. The current GraphQL declaration is incompatible with the remote catalog API, so preflight fails with HTTP 400 even though the configured identity and target exercise are valid.

## What Changes

- Specify that a configured Weight x Reps identity enables complete-catalog exercise resolution before any write.
- Preserve the existing stop-before-write contract when complete-catalog lookup fails.
- Correct the Weight x Reps catalog query to use the remote API's identifier and nested exercise-stat contracts.
- Add regression coverage for the query declaration, variables, nested catalog parsing, and preflight safety.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `weightxreps-cardio-sync`: define complete-catalog resolution when a Weight x Reps user id is configured, including failure before writes.

## Impact

- `src/training_sync/weightxreps/client.py`: Weight x Reps exercise-catalog GraphQL query.
- Weight x Reps client and synchronization tests covering catalog resolution and preflight behavior.
- No CLI syntax, configuration format, credential contents, Garmin data, vault notes, or remote training records are migrated.
