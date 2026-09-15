## Why

Handwritten Garmin plans have worked but exposed errors in transition rests and unilateral recording. Training Sync needs reusable, verified management of strength, cycling/indoor cycling and running workouts supplied through assistant-interpreted chat or screenshots.

## What Changes

- Accept versioned source-independent plans from file or stdin; the assistant interprets Fitbod screenshots/chat, so users need not prepare JSON.
- Support strength sets and rests, cycling/indoor intervals, and running intervals including power, pace and heart-rate targets.
- Add workout create, list, show, update, duplicate and delete for application-created and pre-existing Garmin workouts, subject to permissions.
- Manage calendar entries independently: list, schedule, move, remove and replace a single occurrence with a verified variant while preserving the original template and other dates.
- Default unilateral strength to one step covering both sides with repetitions per side and rest after both; preserve inter-exercise rests.
- Preview execution/differences, verify saved semantics and recover uncertain retries without blind duplication.
- Rely on normal Garmin Connect synchronization; explicit device push is deferred.

## Capabilities

### New Capabilities

- `garmin-planned-workouts`: Source-independent multideporte plans, verified Garmin workout CRUD and independent calendar lifecycle.

### Modified Capabilities

None. Completed-activity and reconciliation requirements remain unchanged.

## Impact

Add planned-workout domain, Garmin adapter, renderer, lifecycle use cases, recovery journal, additive CLI commands and tests using the existing integration. No required vault configuration, OCR/chat parser, completed-activity mutation, Weight x Reps publication or device receipt claim. Existing import-strength and sync interfaces remain unchanged.
