## 1. Baseline and Canonical Training Model

- [x] 1.1 Run `python3 -m pytest -q` and record the existing passing baseline before production edits.
- [x] 1.2 Add failing canonical-model tests in `tests/test_canonical_training_model.py` for completed activity provenance, opaque source artifacts, mixed strength loads, ordered sets, and set/exercise/session effort scope.
- [x] 1.3 Implement the provider-neutral values in `src/training_sync/domain/training.py` and export them through `src/training_sync/domain/__init__.py`.
- [x] 1.4 Run `python3 -m pytest -q tests/test_canonical_training_model.py`; expect the new focused suite to pass.
- [x] 1.5 Create Conventional Commit checkpoint `refactor(domain): add canonical training model`.

## 2. Garmin and Strength Representation Migration

- [x] 2.1 Add failing tests in `tests/test_mapper.py`, `tests/test_strength_workout_plan.py`, and a new `tests/test_strength_import_lifecycle.py` proving Garmin payload decoding is adapter-local and a screenshot-derived import is not completed until Garmin read-back verifies it.
- [x] 2.2 Move Garmin raw-payload decoding behind `src/training_sync/garmin/`, adapt `src/training_sync/domain/garmin_activity.py` callers to the canonical activity, and preserve current fetch and daily rendering behavior.
- [x] 2.3 Move `ParsedTrainingDay`, `ParsedExercise`, and `ParsedSetLine` ownership out of `src/training_sync/renderers/weightxreps_text.py` into canonical strength values while retaining parser and renderer compatibility.
- [x] 2.4 Adapt `src/training_sync/garmin/import_strength.py`, `src/training_sync/renderers/garmin_daily.py`, `src/training_sync/weightxreps/client.py`, and `src/training_sync/weightxreps/jeditor.py` to the canonical values.
- [x] 2.5 Run `python3 -m pytest -q tests/test_mapper.py tests/test_fetch.py tests/test_garmin_daily_renderer.py tests/test_parser.py tests/test_weightxreps_text.py tests/test_weightxreps_client.py tests/test_weightxreps_jeditor.py tests/test_strength_import_lifecycle.py`; expect all focused migration tests to pass.
- [x] 2.6 Create Conventional Commit checkpoint `refactor(training): centralize completed activity representations`.

## 3. Provider-Neutral Exercise Catalog

- [x] 3.1 Add failing tests in `tests/test_exercise_catalog.py` for stable keys, preferred names, aliases, provider bindings, normalized collisions, legacy Weight x Reps mapping reads, backup-before-conversion, and saved read-back.
- [x] 3.2 Implement `src/training_sync/domain/exercise_catalog.py` with neutral exercise identity and provider bindings.
- [x] 3.3 Adapt `src/training_sync/weightxreps/exercise_mapping.py` and `src/training_sync/weightxreps/exercise_resolution.py` to read the legacy format and resolve through the neutral catalog.
- [x] 3.4 Implement explicit safe catalog persistence with timestamped backup, collision validation, and post-write read-back; do not rewrite legacy configuration during read-only resolution.
- [x] 3.5 Run `python3 -m pytest -q tests/test_exercise_catalog.py tests/test_weightxreps_exercise_mapping.py tests/test_weightxreps_exercise_resolution.py`; expect all catalog and compatibility tests to pass.
- [x] 3.6 Create Conventional Commit checkpoint `refactor(exercises): add provider-neutral catalog`.

## 4. Scoped Reconciliation Module

- [x] 4.1 Add failing tests in `tests/test_activity_reconciliation.py` for exact `SyncScope`, the explicit `all` scope, ambiguous scope rejection, deterministic operations, preview-only default, capability rejection, remote fingerprint mismatch, per-target results, and idempotent retry.
- [x] 4.2 Implement canonical reconciliation values in `src/training_sync/domain/reconciliation.py`, including replicas, target scope, operations, destructive consequences, fingerprints, plan, and result states.
- [x] 4.3 Implement capability interfaces and the shared plan/apply/read-back module in `src/training_sync/use_cases/activity_reconciliation.py` without a universal CRUD interface.
- [x] 4.4 Add failing tests proving provider-local edits affect only the selected replica and later canonical reconciliation surfaces drift instead of silently overwriting it.
- [x] 4.5 Implement provider-local edit planning through the same authorization, fingerprint, and verification flow.
- [x] 4.6 Run `python3 -m pytest -q tests/test_activity_reconciliation.py`; expect all reconciliation tests to pass.
- [x] 4.7 Create Conventional Commit checkpoint `feat(sync): add scoped activity reconciliation`.

## 5. Existing Adapter Compatibility

- [x] 5.1 Add failing compatibility tests in `tests/test_use_case_sync_day.py`, `tests/test_weightxreps_push.py`, and `tests/test_vault_training_block.py` proving `sync DATE` retains its current vault and Weight x Reps scope even when another provider is configured.
- [x] 5.2 Adapt Garmin, vault, and Weight x Reps implementations to the new capability seams while preserving current daily existence, replacement confirmation, exercise resolution, full-day reconstruction, and read-back contracts.
- [x] 5.3 Keep `src/training_sync/use_cases/sync_day.py` as a compatibility entry point that delegates shared planning behavior without silently selecting Intervals.icu.
- [x] 5.4 Run `python3 -m pytest -q tests/test_use_case_sync_day.py tests/test_weightxreps_push.py tests/test_weightxreps_preview.py tests/test_vault_training_block.py tests/test_training_sync_cli.py`; expect all existing behavior and new compatibility tests to pass.
- [x] 5.5 Create Conventional Commit checkpoint `refactor(sync): route existing targets through reconciliation`.

## 6. Intervals Read and Identity

- [x] 6.1 Add failing tests in `tests/test_intervals_config.py` and `tests/test_intervals_client.py` for local secret loading, credential redaction, bounded activity inventory, exact get, source-artifact download, response decoding, and actionable read errors.
- [x] 6.2 Add redacted Intervals configuration to `src/training_sync/config.py` and implement the concrete adapter under `src/training_sync/intervals/`.
- [x] 6.3 Add fixture-backed failing tests in `tests/test_intervals_matching.py` for exact remote ID, exact Garmin `external_id`, one-candidate fallback evidence, and multiple-candidate ambiguity.
- [x] 6.4 Implement deterministic Intervals replica matching and fingerprints without automatic deletion on fallback ambiguity.
- [x] 6.5 Run `python3 -m pytest -q tests/test_intervals_config.py tests/test_intervals_client.py tests/test_intervals_matching.py`; expect all read and identity tests to pass.
- [x] 6.6 Create Conventional Commit checkpoint `feat(intervals): add activity inventory and matching`.

## 7. Intervals Create, Update, Delete, and Verification

- [x] 7.1 Add failing tests in `tests/test_intervals_client.py` for multipart upload with Garmin `external_id`, partial supported-field update, Strava update rejection, exact-ID delete, source-sensitive tombstone disclosure, and secret-safe errors.
- [x] 7.2 Implement Intervals upload and independent read-back verification for FIT, TCX, GPX, ZIP, and GZ source artifacts.
- [x] 7.3 Implement partial activity update and reject Strava-sourced update plans before the HTTP mutation.
- [x] 7.4 Implement exact-ID deletion, preview disclosure for Garmin or other external-source tombstones, and deleted-or-absent read-back without automatic tombstone removal.
- [x] 7.5 Add failing use-case tests proving direct Intervals-only CRUD does not mutate Garmin, the vault, Weight x Reps, or TrainingPeaks.
- [x] 7.6 Implement Intervals CRUD operations through scoped reconciliation and verify each target result.
- [x] 7.7 Run `python3 -m pytest -q tests/test_intervals_client.py tests/test_intervals_matching.py tests/test_activity_reconciliation.py`; expect all Intervals lifecycle and isolation tests to pass.
- [x] 7.8 Create Conventional Commit checkpoint `feat(intervals): add verified activity CRUD`.

## 8. CLI Composition and User-Facing Preview

- [x] 8.1 Add failing CLI tests in `tests/test_training_sync_cli.py` for Intervals list/show/upload/update/delete commands, scoped reconciliation with repeatable explicit targets or `all`, preview default, exact-plan authorization, partial results, and redacted failures.
- [x] 8.2 Extend `src/training_sync/cli.py` with Intervals-specific direct lifecycle commands and scoped reconciliation composition while preserving existing command forms.
- [x] 8.3 Render plans with source, exact targets, remote IDs, match reasons, destructive consequences, fingerprints, and the replica retained after duplicate deletion.
- [x] 8.4 Render per-target `verified`, `failed`, and `not_attempted` results and return non-success for partial or verification failure.
- [x] 8.5 Run `python3 -m pytest -q tests/test_training_sync_cli.py tests/test_activity_reconciliation.py tests/test_intervals_client.py`; expect all CLI and orchestration tests to pass.
- [x] 8.6 Create Conventional Commit checkpoint `feat(cli): expose scoped activity lifecycle`.

## 9. Full Verification and Documentation

- [x] 9.1 Run `python3 -m pytest -q`; expect the full suite, including all pre-existing tests, to pass.
- [x] 9.2 Run `openspec validate add-canonical-activity-reconciliation --type change --strict`; expect strict change validation to pass.
- [x] 9.3 Run `openspec validate --specs --strict` and `openspec doctor`; expect existing specifications and repository relationships to remain valid, documenting the inactive `plan` rule warning separately if it persists.
- [x] 9.4 Run `python3 -m build` followed by `python3 -m twine check dist/*`; expect valid wheel and source distribution artifacts.
- [x] 9.5 Run installed CLI smoke tests for existing help, Garmin read-only behavior, Intervals help, and Intervals read-only inventory; no live mutation is part of required verification.
- [x] 9.6 Update `README.md` with canonical authority, Fitbod import, exact target selection, preview/apply behavior, direct provider edits, tombstone consequences, and redacted Intervals configuration.
- [x] 9.7 Perform a final secret scan and `git diff --check`; expect no credentials, generated visual companion files, whitespace errors, or unrelated changes in the implementation diff.
- [x] 9.8 Create Conventional Commit checkpoint `docs(sync): document scoped activity reconciliation`.
