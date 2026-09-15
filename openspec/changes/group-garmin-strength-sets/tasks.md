## 1. Decode and verify repeat semantics

- [ ] 1.1 Add sanitized flat/grouped fixtures and failing tests in `tests/test_garmin_planned_workouts.py` for two/three iterations, final-rest skip, malformed counts, unsupported nesting and bounded expansion; verify failures with `python -m pytest tests/test_garmin_planned_workouts.py` before production edits.
- [ ] 1.2 Implement shared supported-tree decoding in `src/training_sync/garmin/workout_steps.py`; verify the focused tests pass and equivalent fixture expansions match, including manual rests.

## 2. Generate compact strength payloads

- [ ] 2.1 Add failing generator/preview tests in `tests/test_garmin_planned_workouts.py` for equal sets, maximal runs, bodyweight, per-arm load, differing instructions/loads, Bilbo LAP, separate sides, absent rests and unequal transitions; run the file and confirm expected failures.
- [ ] 2.2 Update `src/training_sync/garmin/planned_workouts.py` and `src/training_sync/renderers/planned_workout.py` to emit deterministic groups while retaining expanded steps and canonical hashes; verify the focused tests pass, preview exposes groups, and running/cycling fixtures are unchanged.

## 3. Publication and recovery

- [ ] 3.1 Add failing tests in `tests/test_publish_workout.py` for grouped read-back, altered count/rest/load, flattened saved representation and historical flat journal retry; verify with `python -m pytest tests/test_publish_workout.py`.
- [ ] 3.2 Integrate the shared decoder and layout verification in `src/training_sync/use_cases/publish_workout.py`; verify the focused tests pass and failed verification prevents scheduling while legacy retry does not duplicate or rewrite resources.

## 4. Supported template management

- [ ] 4.1 Locate the existing management tests and add failing coverage there for flat-to-grouped update, grouped load edit, duplicate, variant replacement, stale baseline, metadata conflicts and unsupported groups; run those tests plus `tests/test_planned_calendar.py` and confirm the intended failures.
- [ ] 4.2 Update `src/training_sync/use_cases/manage_planned_workouts.py` to preserve supported metadata and safely handle grouped structures using the shared decoder; verify all new management tests pass with exact resource IDs and preserved unrelated content.

## 5. Integration and delivery

- [ ] 5.1 Add CLI regression coverage in `tests/test_training_sync_cli.py` for preview and authorized grouped writes with fake clients; run the focused tests, then `python -m pytest`, expecting all tests to pass without remote mutations.
- [ ] 5.2 Update `docs/planned-garmin-device-smoke-test.md` with grouped/flat comparison, two-set UI checks and final-rest behavior; verify examples match fixture prescriptions and distinguish saved Garmin evidence from device execution.
- [ ] 5.3 Run `openspec validate group-garmin-strength-sets --strict` and `git diff --check`; review changes against the spec. Respect the code-only Graphify rule: do not run incremental update on a batch containing these Markdown artifacts. If a graph refresh is needed, use deterministic code-only extraction. Report verification and leave commits/push to the requested Git workflow; suggested checkpoints are `feat(garmin): group equivalent strength sets` and `test(garmin): verify grouped workout lifecycle`.
