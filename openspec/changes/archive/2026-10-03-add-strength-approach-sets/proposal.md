## Why

Exercise-specific approach sets currently need a structured planning role so Garmin can distinguish Warm up from Exercise while retaining the exercise, repetitions and load. The user decides when to include approaches; enabling this capability must not add them automatically or change the workout currently being executed.

## What Changes

- Add optional strength-set `role: "warmup" | "work"` under schema version 1, defaulting to work without changing legacy canonical content or publication identity.
- Compile explicit approaches to native Garmin Warm up steps with their prescribed exercise, load, repetition/manual/time termination and rests.
- Keep equal warmup and working prescriptions in distinct repeat groups and verify the native role on read-back before scheduling.
- Document the user's opt-in preference in repository instructions and the hybrid-training-advisor skill.
- Preserve the independent generic workout warm-up. Do not infer roles, add approaches to existing plans, modify the current Garmin workout or classify completed activities.

## Capabilities

### New Capabilities

None; extend the existing planning and grouping capabilities.

### Modified Capabilities

- `garmin-planned-workouts`: explicit exercise-specific approach roles, backward-compatible identity, preview and read-back preservation.
- `garmin-strength-set-grouping`: role equality becomes an explicit grouping condition.

## Impact

- Domain: `src/training_sync/domain/planned_workout.py`.
- Garmin compiler: `src/training_sync/garmin/planned_workouts.py`; existing publication and management verification are reused.
- Tests: `tests/test_planned_workout.py`, `tests/test_garmin_planned_workouts.py`, `tests/test_publish_workout.py`, `tests/test_manage_planned_workouts.py`.
- Guidance: `AGENTS.md`, `README.md`, and the user-authorized global skill `/Users/birrein/.codex/skills/hybrid-training-advisor/SKILL.md`.
- No dependencies, real Garmin writes, calendar changes, vault edits or Weight x Reps writes are required.

Traceability note: the implementation and focused tests already exist as uncommitted working-tree changes when this formal change is created. This proposal records that observed state; it does not imply the proposal preceded implementation or that device execution has been tested.
