## 1. Provider serialization contract

- [x] 1.1 Add sanitized rejected/accepted/read-back fixtures under `tests/fixtures/garmin/` and failing cases in `tests/test_garmin_planned_workouts.py` for unit objects, termination fields, internal metadata exclusion and Dragon Flag comments; verify failures with `uv run python -m pytest tests/test_garmin_planned_workouts.py -q` before production edits. Include evidence notes distinguishing combined successful corrections from isolated causal proof.
- [x] 1.2 Implement provider-compatible serialization in `src/training_sync/garmin/planned_workouts.py`, recursively handling supported groups without changing domain hashes; verify the focused suite passes and previews preserve loads, sides, termination and rests. Include cycling/running regression cases. Suggested commit checkpoint: `fix(garmin): serialize compatible workout payloads`.

## 2. Verification and recovery

- [x] 2.1 Add failing tests in `tests/test_publish_workout.py` for structured/legacy units, unknown or contradictory units, omitted adapter metadata, altered comments, per-hand semantics and mismatched mass; verify failures before changing `src/training_sync/use_cases/publish_workout.py`, then implement normalization and obtain a passing focused suite with `uv run python -m pytest tests/test_publish_workout.py -q`.
- [x] 2.2 Add a provider-shaped boundary fake and failing recovery tests in `tests/test_publish_workout.py` and `tests/test_planned_calendar.py`: uncertain journal plus one exact corrected remote match, existing schedule reuse, incomplete/ambiguous inventory and missing rests must exercise read-back without duplicate writes. Correct recovery only where required and verify both suites pass. Suggested commit checkpoint: `fix(garmin): verify provider units and recover publications`.

## 3. All write paths and diagnostics

- [x] 3.1 Add failing request/response compatibility cases in `tests/test_manage_planned_workouts.py` for update, duplicate and date-specific variant writes, including supported repeat children and preservation of unrelated metadata; align shared boundaries in `src/training_sync/use_cases/manage_planned_workouts.py` and verify `uv run python -m pytest tests/test_manage_planned_workouts.py tests/test_planned_calendar.py -q` passes. Compose with the selected grouping baseline without changing its rest policy.
- [x] 3.2 Add failing diagnostics tests covering HTTP 500 / MismatchedInputException, provider reference IDs, timeout-only failures, redaction, bounded output and journal persistence. Implement safe extraction through publication/management results and `src/training_sync/cli.py` as needed; verify focused tests retain the original failure alongside reconciliation and do not leak embedded secrets. Suggested commit checkpoint: `fix(garmin): retain safe workout failure diagnostics`.

## 4. Integration and documentation

- [x] 4.1 Update `README.md` with corrected-payload behavior, actionable failure output and uncertain-retry guidance; verify documented commands match the CLI and no instruction resets journals or bypasses duplicate protection.
- [x] 4.2 Run `uv run python -m pytest -q` and `openspec validate fix-garmin-workout-payload --strict`; expect both to pass. Record validation evidence, flat/grouped coverage and remaining live/device limitations in the change. If the recovered workout remains accessible, perform read-only template/calendar verification without uploading test workouts. Suggested documentation checkpoint: `docs(garmin): document workout payload recovery`.
