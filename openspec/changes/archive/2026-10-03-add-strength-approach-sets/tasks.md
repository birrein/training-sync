## 1. Acceptance coverage and baseline

The ordering below is the required dependency order. In this change the implementation predated formal planning and the baseline failing test run. Checked items record observed completion, not historical test-first compliance. Any further production edit requires a relevant failing test first and a focused passing test afterward.

- [x] 1.1 Define acceptance scenarios in both delta specs; verify coverage of explicit roles, legacy identity, provider role loss and grouping boundaries.
- [x] 1.2 Add regression tests in `tests/test_planned_workout.py` and `tests/test_garmin_planned_workouts.py`; verify the role round-trip and native Warm up tests fail against an isolated copy using the pre-role domain from HEAD. Observed result: two failures for unknown field role; the real checkout was not reverted. This baseline was run after implementation, as disclosed above.

## 2. Domain and Garmin projection

- [x] 2.1 Add optional set role validation, repeat preservation and canonical serialization in `src/training_sync/domain/planned_workout.py`; verify omitted and explicit work preserve legacy identity, warmup survives round-trip and invalid roles report field paths in `tests/test_planned_workout.py`.
- [x] 2.2 Map explicit approaches to native Warm up strength steps in `src/training_sync/garmin/planned_workouts.py`; verify exercise, load, generic warm-up independence and repetition/manual/time termination in `tests/test_garmin_planned_workouts.py`.
- [x] 2.3 Preserve role boundaries in grouped strength prescriptions; verify same-role grouping, combined unilateral semantics and existing transition-rest behavior in `tests/test_garmin_planned_workouts.py`.

## 3. Provider boundary and management

- [x] 3.1 Cover approach publication and corrupted role read-back in `tests/test_publish_workout.py`; verify the fake provider preserves Warm up and refuses scheduling when it becomes Exercise. No real provider mutation is needed.
- [x] 3.2 Cover update and duplication in `tests/test_manage_planned_workouts.py`; verify grouped approach roles, changed load and unrelated metadata survive both operations.

## 4. Guidance and integration verification

- [x] 4.1 Document the opt-in policy and schema in `AGENTS.md`, `README.md` and `/Users/birrein/.codex/skills/hybrid-training-advisor/SKILL.md`; verify they require a user request and distinguish planned roles from completed classification. Validate the skill with `python3 /Users/birrein/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/birrein/.codex/skills/hybrid-training-advisor`; observed result: Skill is valid.
- [x] 4.2 Run `.venv/bin/python -m pytest -q tests/test_planned_workout.py tests/test_garmin_planned_workouts.py tests/test_publish_workout.py tests/test_manage_planned_workouts.py tests/test_planned_boundaries.py tests/test_planned_calendar.py`; observed result: 174 passed. Tests cover domain, projection, provider verification and management offline.
- [x] 4.3 Run `openspec validate add-strength-approach-sets --strict` and `git diff --check`; both succeeded. Inspect final OpenSpec status for all four artifacts before reporting formalization complete.
