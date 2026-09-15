## 0. Extend compact input

- [x] 0.1 Add failing tests in `tests/test_planned_workout.py` for omitted repeat, repeat=1 and N, mixed entries, repeated time/LAP and side rounds, invalid counts (including bool/float/string/null), bounded aggregate expansion, and compact/explicit canonical hash equality; confirm focused failures before production edits.
- [x] 0.2 Extend `src/training_sync/domain/planned_workout.py` normalization to expand optional repeat into physical sets with stable canonical serialization; run `python -m pytest tests/test_planned_workout.py -q` and verify all cases pass, including unchanged hashes for old explicit inputs.

## 1. Decode and verify repeat semantics

- [x] 1.1 Add sanitized flat/grouped fixtures and failing tests in `tests/test_garmin_planned_workouts.py` for N iterations (including 2, 3, 4 and 5), retained final rests, legacy skipped-rest decoding, malformed counts, unsupported nesting and bounded expansion; verify failures with `python -m pytest tests/test_garmin_planned_workouts.py` before production edits.
- [x] 1.2 Implement shared supported-tree decoding in `src/training_sync/garmin/workout_steps.py`; verify the focused tests pass and equivalent fixture expansions match, including manual rests.

## 2. Generate compact strength payloads

- [x] 2.1 Add failing generator/preview tests in `tests/test_garmin_planned_workouts.py` for equal sets, maximal runs, bodyweight, per-arm load, differing instructions/loads, Bilbo LAP followed by rest, separate sides, rejection of missing/null rests and separate final sets for unequal transitions; run the file and confirm expected failures.
- [x] 2.2 Update `src/training_sync/garmin/planned_workouts.py` and `src/training_sync/renderers/planned_workout.py` to require explicit strength rests and emit deterministic groups with skipLastRestStep=false; verify the focused tests pass, preview exposes final rests, unchanged prescriptions retain their hashes, and running/cycling fixtures are unchanged.

## 3. Publication and recovery

- [x] 3.1 Add failing tests in `tests/test_publish_workout.py` for grouped read-back, altered count/rest/load, flattened saved representation, historical flat journal retry, and same-key compact/explicit retry without a duplicate upload; verify with `python -m pytest tests/test_publish_workout.py`.
- [x] 3.2 Integrate the shared decoder and layout verification in `src/training_sync/use_cases/publish_workout.py`; verify the focused tests pass and failed verification prevents scheduling while legacy retry does not duplicate or rewrite resources.

## 4. Supported template management

- [x] 4.1 Locate the existing management tests and add failing coverage there for flat-to-grouped update, grouped load edit, duplicate, variant replacement, stale baseline, metadata conflicts and unsupported groups; run those tests plus `tests/test_planned_calendar.py` and confirm the intended failures.
- [x] 4.2 Update `src/training_sync/use_cases/manage_planned_workouts.py` to preserve supported metadata and safely handle grouped structures using the shared decoder; verify all new management tests pass with exact resource IDs and preserved unrelated content.

## 5. Integration and delivery

- [x] 5.1 Add CLI regression coverage in `tests/test_training_sync_cli.py` for compact/explicit file and stdin parity, invalid repeat before authentication, preview and authorized grouped writes with fake clients; run the focused tests, then `python -m pytest`, expecting all tests to pass without remote mutations.
- [x] 5.2 Update `README.md` and `examples/planned-strength.json` with optional repeat, mixed sets, the documented expansion bound and explicit final rests; verify equivalent expanded/compact offline previews. Update `docs/planned-garmin-device-smoke-test.md` with N-set UI checks and editing weight/repetitions during final rest, attributing the 2026-09-14 observation to the user.
- [x] 5.3 Run `openspec validate group-garmin-strength-sets --strict` and `git diff --check`; review changes against the spec. Respect the code-only Graphify rule: do not run incremental update on a batch containing these Markdown artifacts. If a graph refresh is needed, use deterministic code-only extraction. Report verification and leave commits/push to the requested Git workflow; suggested checkpoints are `feat(garmin): group equivalent strength sets` and `test(garmin): verify grouped workout lifecycle`.
