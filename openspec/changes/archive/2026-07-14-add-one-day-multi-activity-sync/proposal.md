## Why

The CLI exposes `sync DATE`, but its dispatcher does not implement the integrated day flow. Cycling blocks also break the current Weight x Reps parser, and a valid training day may contain multiple Garmin activities. The active design must therefore cover the whole day and use Weight x Reps' structured cardio fields instead of a marker-only workaround.

## What Changes

- Dispatch `training-sync sync DATE [--yes]` into a testable one-day orchestration use case.
- Reconcile every completed Garmin activity for the date into the existing daily note in stable order and in one training section.
- Generate structured Weight x Reps cardio rows with real duration and, when available, distance and unit.
- Reconstruct the complete Weight x Reps day so strength and all cardio activities are preserved.
- Preflight all inputs and confirmations before writes, then verify the remote day by read-back and report expected versus observed mismatches.

## Capabilities

### New Capabilities

- `daily-multi-activity-sync`: Garmin activity selection, ordering, preflight, confirmation, combined daily rendering, and partial-failure behavior.
- `weightxreps-cardio-sync`: Structured cardio conversion, full-day preservation, remote replacement, and field-level read-back verification.

### Modified Capabilities

None. The project has no stable capability specifications under `openspec/specs/` yet.

## Impact

The change affects the CLI contract, one-day sync use case, Garmin-to-daily rendering, Weight x Reps text parser, JEditor conversion and client verification, focused and end-to-end tests, and later README usage documentation. It introduces no new external dependency and performs no external writes during planning.
