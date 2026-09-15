## Why

Garmin supports compact repeat groups, but training-sync currently publishes every strength set separately. Consecutive equivalent sets should display as “N Sets”, where N is the number of sets in the group (any integer of at least two, such as 2, 3, 4 or 5), while preserving the exact exercise and rest sequence.

## What Changes

- Automatically group consecutive equivalent strength sets into Garmin RepeatGroupDTO blocks.
- Extend each input `sets` entry with optional positive-integer `repeat` (default 1); normalize compact and explicit forms to the same physical sets and execution hash.
- Preserve explicit prescriptions and expose grouping in preview; require a defined rest after every strength set before new writes.
- Preserve transition and final rests with skipLastRestStep=false so the watch offers its post-set weight/repetition editing phase.
- Verify grouped remote payloads and safely update supported flat/grouped templates through existing authorized workflows.
- Keep mixed loads, manual Bilbo sets and unsupported grouping cases separate.

## Capabilities

### New Capabilities

- `garmin-strength-set-grouping`: Compact strength representation, equivalence verification and safe grouped-template lifecycle.

### Modified Capabilities

- `garmin-planned-workouts`: Extend source-independent input with optional per-set `repeat` and require explicit rests on new strength writes. The delta also replaces the prior null-terminal-rest scenario. Historical payloads remain readable without migration.

## Impact

Touches `src/training_sync/domain/planned_workout.py`, the Garmin adapter, planned-workout renderer, publication verification, template management and their tests. `repeat` is an additive extension to schema version 1: updated readers accept old explicit lists, while older strict readers reject the new field. The required-rest policy changes validation for new strength writes. No new dependency is expected. Running/cycling grouping and automatic migration of existing remote workouts are outside scope. Existing Garmin authorization, journal, stale-baseline and calendar boundaries remain applicable.
