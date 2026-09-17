## Why

A real strength-workout publication on 2026-09-16 failed with HTTP 500 / MismatchedInputException despite passing offline preview. A corrected request using Garmin's accepted unit representation succeeded and was read back and scheduled; the CLI currently hides the useful provider error behind an uncertain outcome.

## What Changes

- Serialize planned workouts using provider-compatible unit objects and termination fields, keeping internal metadata outside the wire payload while preserving user-visible exercise instructions.
- Verify remote unit representations by normalized meaning, including total/per-hand loads and bodyweight, without masking mismatches.
- Retain bounded, redacted HTTP/provider diagnostics independently of reconciliation status.
- Preserve publication identity and duplicate prevention, including existing uncertain journal entries and the manually recovered publication.
- Cover flat and supported repeated strength steps, and protect running/cycling behavior with regression tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `garmin-planned-workouts`: Specify provider-compatible serialization, unit-aware read-back and actionable diagnostics while retaining safe recovery.

## Impact

- `src/training_sync/garmin/planned_workouts.py`, `src/training_sync/use_cases/publish_workout.py`, and shared write/read-back paths in `src/training_sync/use_cases/manage_planned_workouts.py`.
- Tests for projection, publication, template management and calendar recovery; README troubleshooting guidance.
- Coordinate with the existing `group-garmin-strength-sets` change without rewriting its dirty planning artifacts or changing its grouping/rest policy.
- No public input-schema change, completed-activity changes, new exercise mapping, device-push feature or automatic migration of remote workouts.
