## Why

Garmin supports compact repeat groups, but training-sync currently publishes every strength set separately. Identical sets should display as “2 Sets” while preserving the exact exercise and rest sequence.

## What Changes

- Automatically group consecutive equivalent strength sets into Garmin RepeatGroupDTO blocks.
- Keep canonical input and expanded execution unchanged; preview also exposes grouping.
- Preserve transition rests and omit an absent final rest using skipLastRestStep.
- Verify grouped remote payloads and safely update supported flat/grouped templates through existing authorized workflows.
- Keep mixed loads, manual Bilbo sets and unsupported grouping cases separate.

## Capabilities

### New Capabilities

- `garmin-strength-set-grouping`: Compact strength representation, equivalence verification and safe grouped-template lifecycle.

### Modified Capabilities

None in the current main inventory. The prerequisite `garmin-planned-workouts` capability exists only in the completed, unarchived `add-garmin-planned-workouts` change. This additive capability builds on that contract without changing its artifacts or duplicating its lifecycle requirements.

## Impact

Touches `src/training_sync/garmin/planned_workouts.py`, the planned-workout renderer, publication verification, template management and their tests. No new dependency or input schema version is expected. Running/cycling grouping and automatic migration of existing remote workouts are outside scope. Existing Garmin authorization, journal, stale-baseline and calendar boundaries remain applicable.
