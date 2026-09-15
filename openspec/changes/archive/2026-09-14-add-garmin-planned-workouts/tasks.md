## 1. Portable planned-workout contract

- [x] 1.1 Add failing tests in tests/test_planned_workout.py for versioned input, independent provenance, unequal sets, per-hand/bodyweight loads, timed/manual-lap sets, cycling/running time/distance intervals, explicit targets including running watts, repeated blocks, invalid numeric values, unknown fields and explicit rest choices; verify the focused test run fails for missing behavior before production edits.
- [x] 1.2 Implement src/training_sync/domain/planned_workout.py with strict normalization; verify `python -m pytest tests/test_planned_workout.py -q` passes and no vault/provider imports enter the domain.

## 2. Executable preview and Garmin projection

- [x] 2.1 Add failing sequence tests in tests/test_garmin_planned_workouts.py for RDL transition rest, combined unilateral sets by default, explicit separate-side rounds, varied loads, final-rest omission, timed/lap steps and unresolved/substituted exercise names; verify expected complete step sequences fail before implementation.
- [x] 2.2 Implement src/training_sync/garmin/planned_workouts.py and src/training_sync/renderers/planned_workout.py with multideporte flattened steps, target units/bounds, catalog-backed resolution and visible load basis; verify focused sequence tests pass and preview exactly matches projected semantics.

## 3. Verified publication and retry recovery

- [x] 3.1 Add failing fake-client tests in tests/test_publish_workout.py for changed read-back rests, successful template-only creation, explicit dates, scheduling failure, lost upload responses, ambiguous remote matches, repeated publication and concurrent-key locking; verify failures before implementing the lifecycle.
- [x] 3.2 Implement src/training_sync/use_cases/publish_workout.py and adapter read-back comparison, preserving independent template/calendar statuses and IDs; verify fake-client tests reject mismatches without scheduling or deleting remote data.
- [x] 3.3 Add an atomic account-scoped journal and lock under configured local storage, expose its path via src/training_sync/config.py, and recover uncertain outcomes using a remote marker; verify same-key retry and conflict tests pass and secrets/source prose are absent from the journal marker and output.

## 4. Existing workout CRUD and calendar lifecycle

- [x] 4.1 Add failing tests in tests/test_manage_planned_workouts.py for bounded paginated inventory, exact IDs, pre-existing workouts, permission failures, metadata preservation, unsupported remote structures, stale baselines, template-wide update, duplicate and protected deletion; verify failures before production edits.
- [x] 4.2 Implement src/training_sync/use_cases/manage_planned_workouts.py and extend src/training_sync/garmin/planned_workouts.py for verified template operations and semantic differences; verify `python -m pytest tests/test_manage_planned_workouts.py -q` passes without live mutations.
- [x] 4.3 Add failing tests in tests/test_planned_calendar.py for local dates, multiple entries, schedule retry, move/remove preserving templates, one-date variants preserving other dates, and every partial-failure boundary of create/verify/schedule/verify/remove; verify focused failures before implementation.
- [x] 4.4 Extend lifecycle orchestration and account-scoped journal/locks for calendar and CRUD operations, fresh baseline checks, uncertain deletion and resumable replacements; verify `python -m pytest tests/test_planned_calendar.py tests/test_manage_planned_workouts.py tests/test_publish_workout.py -q` passes with no blind duplication or automatic orphan deletion.
- [x] 4.5 Add failing adapter tests for running power units/ranges, pace conversion, cycling cadence compatibility, repeated recoveries, unknown thresholds and provider step limits; implement supported mappings and explicit rejection paths, then verify tests/test_garmin_planned_workouts.py passes without truncation or target omission.

## 5. CLI and usage contract

- [x] 5.1 Add failing tests in tests/test_training_sync_cli.py for complete workout CRUD and calendar list/schedule/move/remove/replace, file/stdin parity, offline preview without vault or tokens, --yes semantics, source-independent dates and failure exit codes; verify focused failures before CLI changes.
- [x] 5.2 Wire additive commands in src/training_sync/cli.py; verify CLI tests pass and existing import-strength/sync behavior is preserved.
- [x] 5.3 Add examples/planned-strength.json, examples/planned-cycling.json, examples/planned-running-power.json and README.md instructions showing chat/screenshot/note → assistant-prepared JSON → preview → publication, plus local retry scope and device-sync limitations; verify the example through the offline preview command.

## 6. Integration verification

- [x] 6.1 Run `python -m pytest -q` and `openspec validate add-garmin-planned-workouts --strict`; verify all checks pass and record results without publishing a live workout.
- [x] 6.2 Document an opt-in device smoke-test procedure covering RDL transition, combined unilateral sets, cycling intervals and running power; verify the procedure distinguishes API read-back from observed watch behavior and does not reuse an active workout.

- [x] 6.3 Verify CLI/adapter tests assert no device push, completed-activity, vault or Weight x Reps writes across every planned operation; record the tests and separately document actual-device compatibility as unverified until an explicitly authorized smoke test succeeds.
