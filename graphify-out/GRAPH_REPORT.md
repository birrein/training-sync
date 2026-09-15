# Graph Report - training-sync  (2026-09-14)

## Corpus Check
- 207 files · ~171,564 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .lock 1)

## Summary
- 2386 nodes · 4246 edges · 189 communities (152 shown, 23 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 295 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `12076728`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- weightxreps/exercise_mapping.py
- test_use_case_sync_day.py
- WeightxRepsClient
- IntervalsClient
- import_strength.py
- ParsedSetLine
- test_training_sync_cli.py
- weight.py
- activity_reconciliation.py
- domain/__init__.py
- FakeWeightxRepsClient
- cli.py
- config.py
- garmin_daily.py
- weightxreps_preview.py
- manage_planned_workouts.py
- test_config.py
- FakeWeightxReps
- test_garmin_auth.py
- test_weightxreps_auth.py
- sync_day.py
- renderers/__init__.py
- use_cases/__init__.py
- vault/__init__.py
- weightxreps/__init__.py
- training-sync
- publish_workout.py
- planned_workouts.py
- superpowers-bridge Schema
- Requirements
- domain/planned_workout.py
- Requirements
- ADDED Requirements
- planned_workout_from_dict
- Requirements
- ADDED Requirements
- Requirements
- ADDED Requirements
- Requirements
- What You Must Do When Invoked
- ADDED Requirements
- ExerciseResolutionRequired
- FakeManagementClient
- Decisions
- ADDED Requirements
- ADDED Requirements
- Requirements
- GarminActivity
- File Structure
- File Structure
- Training Sync Weight x Reps Integration Design
- ADDED Requirements
- Decisions
- Usage
- Weight x Reps Exercise Resolution Design
- One-Day Sync and Cycling Support Design
- add-garmin-planned-workouts/design.md
- Decisions
- Verification Report
- ExerciseCatalog
- test_planned_workout.py
- Component Details
- Decision chain
- Requirements
- ADDED Requirements
- Requirements
- Requirements
- PlannedWorkout
- openspec-explore/SKILL.md
- 2026-07-21-complete-training-sync-migration/design.md
- ADDED Requirements
- 2026-07-31-centralize-local-configuration/design.md
- Verification Report
- ADDED Requirements
- 2026-07-31-migrate-to-uv/design.md
- ADDED Requirements
- Retrospective: add-one-day-multi-activity-sync
- 2026-07-31-add-canonical-activity-reconciliation/tasks.md
- Retrospective: centralize-local-configuration
- 2026-09-13-fix-weightxreps-set-semantics-and-sync-link/design.md
- Retrospective: <change-name>
- templates/spec.md
- Verification Report
- graphify reference: extra exports and benchmark
- Verification Report
- Verification Report
- Garmin Sync Modular Refactoring Implementation Plan
- File Map
- Garmin Sync Automation Design
- Global Constraints
- Retrospective: direct-cli-install
- Approaches considered
- Retrospective: migrate-to-uv
- superpowers-bridge Schema
- Apply phase walkthrough
- templates/design.md
- add-garmin-planned-workouts/proposal.md
- ADDED Requirements
- add-garmin-planned-workouts/tasks.md
- 2026-07-14-add-one-day-multi-activity-sync/proposal.md
- 2026-07-21-complete-training-sync-migration/proposal.md
- 2026-07-21-complete-training-sync-migration/tasks.md
- 2026-07-22-fix-weightxreps-full-catalog-lookup/proposal.md
- 2026-07-22-improve-weightxreps-graphql-errors/proposal.md
- 2026-07-31-add-canonical-activity-reconciliation/proposal.md
- 2026-07-31-centralize-local-configuration/proposal.md
- Design: direct-cli-install
- 2026-07-31-migrate-to-uv/proposal.md
- 2026-09-13-fix-weightxreps-set-semantics-and-sync-link/proposal.md
- group-garmin-strength-sets/proposal.md
- Six design touches worth remembering
- templates/proposal.md
- UnresolvedExercise
- planned_json
- graphify reference: query, path, explain
- Garmin Sync Python Script Implementation Plan
- Requirement: Preview the executable sequence
- 2026-07-14-add-one-day-multi-activity-sync/tasks.md
- Global Constraints
- Global Constraints
- group-garmin-strength-sets/design.md
- group-garmin-strength-sets/tasks.md
- Workflow routing (read on session start)
- 變更工作流(Claude Code 啟動先讀)
- Requirement: Represent multideporte interval prescriptions
- Requirement: Update and duplicate workouts safely
- 2026-07-22-fix-weightxreps-full-catalog-lookup/design.md
- Requirement: Resolve exercises using the complete catalog
- 2026-07-22-improve-weightxreps-graphql-errors/design.md
- Requirement: Surface Weight x Reps GraphQL errors
- Retrospective design capture: centralize-local-configuration
- Proposal: direct-cli-install
- Workflow & integration
- Repository instructions
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- Planned Garmin device smoke test
- Requirement: Manage calendar occurrences independently
- Requirement: Verify creation and scheduling independently
- 2026-07-22-fix-weightxreps-full-catalog-lookup/tasks.md
- 2026-07-22-improve-weightxreps-graphql-errors/tasks.md
- Local Configuration Retrospective Plan
- 2026-07-31-direct-cli-install/tasks.md
- 2026-07-31-migrate-to-uv/tasks.md
- 2026-09-13-fix-weightxreps-set-semantics-and-sync-link/tasks.md
- Design decisions worth knowing
- Entry & exit gates
- Usage
- Upgrading an existing install
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- Requirement: Accept source-independent planned input
- Requirement: Delete only exact authorized templates
- Requirement: Inventory existing and application-created resources
- Requirement: Isolate single-date prescription changes
- Requirement: Preserve exercise identity and load semantics
- Requirement: Recover without blind duplication
- Requirement: Verify all mutations and recover partial outcomes
- cutover.md
- 2026-07-31-centralize-local-configuration/tasks.md
- Compatibility
- Install
- [Feature Name] Implementation Plan
- templates/tasks.md
- LoadSpec
- test_intervals_list_and_show_are_read_only
- test_intervals_update_is_preview_by_default_and_apply_is_verified
- FakeGarmin
- extraction-spec.md
- UPSTREAM.md
- test_training_sync_rejects_legacy_arguments_before_constructing_clients
- test_preview_weightxreps_day_uses_remote_exercise_ids
- test_push_weightxreps_day_cli_prints_direct_weightxreps_url
- test_training_sync_garmin_import_strength_reports_data_errors

## God Nodes (most connected - your core abstractions)
1. `planned_workout_from_dict()` - 52 edges
2. `project_planned_workout()` - 47 edges
3. `publish_workout()` - 47 edges
4. `preflight_sync_day()` - 46 edges
5. `activity()` - 35 edges
6. `ExerciseMapping` - 34 edges
7. `fake_dependencies()` - 34 edges
8. `WeightxRepsClient` - 32 edges
9. `PlannedWorkoutValidationError` - 29 edges
10. `ParsedSetLine` - 28 edges

## Surprising Connections (you probably didn't know these)
- `test_weightxreps_parser_values_are_canonical_domain_values()` --uses--> `ParsedTrainingDay`  [INFERRED]
  tests/test_strength_workout_plan.py → src/training_sync/domain/training.py
- `test_push_weightxreps_day_cli_passes_explicit_user_id()` --uses--> `TokenSet`  [INFERRED]
  tests/test_training_sync_cli.py → src/training_sync/weightxreps/auth.py
- `test_push_weightxreps_day_cli_uses_env_user_id_fallback()` --uses--> `TokenSet`  [INFERRED]
  tests/test_training_sync_cli.py → src/training_sync/weightxreps/auth.py
- `test_weightxreps_client_refresher_saves_new_tokens()` --uses--> `TokenSet`  [INFERRED]
  tests/test_training_sync_cli.py → src/training_sync/weightxreps/auth.py
- `test_preview_weightxreps_day_uses_remote_exercise_ids()` --indirect_call--> `vault_root()`  [INFERRED]
  tests/test_training_sync_cli.py → src/training_sync/config.py

## Import Cycles
- None detected.

## Communities (189 total, 23 thin omitted)

### Community 0 - "weightxreps/exercise_mapping.py"
Cohesion: 0.13
Nodes (35): Push a vault training day to Weight x Reps., add_alias_mapping(), add_create_mapping(), _backup_if_exists(), _catalog_signature(), _dump_exercise_mapping(), _dump_exercise_mappings(), _duplicate_targets() (+27 more)

### Community 1 - "test_use_case_sync_day.py"
Cohesion: 0.20
Nodes (34): preflight_sync_day(), activity(), assert_no_writes(), fake_dependencies(), parametrize, Path, test_apply_retry_saves_identical_rows_after_partial_failure(), test_apply_returns_verified_result_after_matching_remote_readback() (+26 more)

### Community 2 - "WeightxRepsClient"
Cohesion: 0.07
Nodes (49): build_journal_url(), _default_date_from_rows(), _empty_comment_default(), _normalize_expected_blocks(), _normalize_expected_set(), _normalize_observed_blocks(), _normalize_observed_set(), Any (+41 more)

### Community 3 - "IntervalsClient"
Cohesion: 0.08
Nodes (29): BinaryIO, IntervalsActivity, IntervalsClient, IntervalsError, IntervalsNotFoundError, IntervalsUnsupportedUpdateError, Any, RuntimeError (+21 more)

### Community 4 - "import_strength.py"
Cohesion: 0.07
Nodes (40): Any, Strength workout domain objects and input normalization., Normalize Fitbod-like workout data into a strength workout., strength_workout_from_dict(), StrengthExercise, StrengthSet, StrengthWorkout, get_mapping() (+32 more)

### Community 5 - "ParsedSetLine"
Cohesion: 0.13
Nodes (39): ParsedExercise, ParsedSetLine, ParsedTrainingDay, _parse_duration_ms(), _parse_exercise_block(), _parse_set_line(), parse_weightxreps_text(), finish_exercise() (+31 more)

### Community 6 - "test_training_sync_cli.py"
Cohesion: 0.10
Nodes (3): test_push_weightxreps_day_cli_passes_explicit_user_id(), test_push_weightxreps_day_cli_uses_env_user_id_fallback(), test_weightxreps_client_refresher_saves_new_tokens()

### Community 7 - "weight.py"
Cohesion: 0.09
Nodes (29): format_weight_tag(), Body-weight domain objects., WeightReading, ActivityMetric, Normalized training log entries., TrainingEntry, _body_weight_tag(), fetch_and_print_activities() (+21 more)

### Community 8 - "activity_reconciliation.py"
Cohesion: 0.16
Nodes (23): OperationKind, StrEnum, Values used to preview and safely apply scoped reconciliation., ReconciliationOperation, ReconciliationPlan, ReconciliationResult, SyncScope, TargetResult (+15 more)

### Community 9 - "domain/__init__.py"
Cohesion: 0.14
Nodes (24): datetime, Pure training-sync domain objects., CompletedActivity, EffortObservation, EffortScope, Load, LoadKind, promote_verified_strength_import() (+16 more)

### Community 10 - "FakeWeightxRepsClient"
Cohesion: 0.19
Nodes (18): push_weightxreps_day(), Path, FakeWeightxRepsClient, Path, test_push_weightxreps_day_creates_explicitly_mapped_new_exercise(), test_push_weightxreps_day_does_not_create_with_partial_jeditor_catalog(), test_push_weightxreps_day_does_not_write_unresolved_exercises(), test_push_weightxreps_day_prefers_explicit_exercise_ids_over_catalog() (+10 more)

### Community 11 - "cli.py"
Cohesion: 0.12
Nodes (32): ArgumentParser, _add_modern_subcommands(), auth_weightxreps_cli(), build_intervals_client(), _build_parser(), build_weightxreps_client(), refresh_token(), _dispatch() (+24 more)

### Community 12 - "config.py"
Cohesion: 0.17
Nodes (25): _configured_vault_root(), _exit_with_resolution_payload(), preview_weightxreps_day(), push_weightxreps_day_cli(), sync_day_cli(), _weightxreps_url(), config_dir(), garmin_token_path() (+17 more)

### Community 13 - "garmin_daily.py"
Cohesion: 0.14
Nodes (22): ActivityClassification, classify_activity_type(), Shared Garmin activity classification for rendering and Weight x Reps., _activity_tag(), _duration_text(), _metric_text(), _pace_text(), Pure rendering for ordered Garmin activities in a daily training section. (+14 more)

### Community 14 - "weightxreps_preview.py"
Cohesion: 0.10
Nodes (27): _extract_text_blocks(), load_weightxreps_day_from_vault(), preview_weightxreps_day_from_vault(), Any, Path, Preview Weight x Reps rows from a vault daily note., daily_note_path(), Path (+19 more)

### Community 15 - "manage_planned_workouts.py"
Cohesion: 0.06
Nodes (97): Namespace, _planned_calendar_cli(), _planned_template_cli(), planned_workout_cli(), _print_planned_result(), _print_structured(), Dispatch planned workout commands with preview-first semantics., Print a lifecycle result and use a nonzero exit for non-success states. (+89 more)

### Community 16 - "test_config.py"
Cohesion: 0.20
Nodes (4): Training synchronization across Garmin, Obsidian, and Weight x Reps., parametrize, test_vault_root_rejects_relative_configuration(), test_vault_root_requires_configuration_when_both_sources_are_absent()

### Community 19 - "test_weightxreps_auth.py"
Cohesion: 0.24
Nodes (5): FakeResponse, FakeSession, test_build_authorization_url_contains_weightxreps_params(), test_exchange_code_for_tokens_posts_pkce_form(), test_refresh_access_token_posts_refresh_token_form()

### Community 21 - "sync_day.py"
Cohesion: 0.20
Nodes (17): apply_sync_plan(), _exercises_by_id(), PartialSyncFailure, Exception, Path, RuntimeError, Preflight-first orchestration for one-day synchronization., _reconcile_preserved_training_day() (+9 more)

### Community 29 - "publish_workout.py"
Cohesion: 0.06
Nodes (70): GarminWorkoutProjection, A deterministic payload plus the exact steps shown in preview., _account_key(), build_publication_marker(), _calendar_items(), _coerce_workout(), _compare_step(), _description_carries_semantic() (+62 more)

### Community 30 - "planned_workouts.py"
Cohesion: 0.10
Nodes (44): PlannedSet, PlannedStep, How an active or rest step ends., An intensity target kept separate from step termination., TargetSpec, Termination, _append_strength_exercise(), _base_step() (+36 more)

### Community 31 - "superpowers-bridge Schema"
Cohesion: 0.04
Nodes (48): 0. Pre-flight — 驗證必要的 Superpowers skill, 1. Skill-name PRECHECK(Layer 1 capability detection), 1. Workspace — `superpowers:using-git-worktrees`, 2. Executor — `superpowers:subagent-driven-development`, 2. Schema-level vs prompt-level 整合, 3. Verification — `openspec-verify-change`, 3. 傳遞依賴顯式化, 4. Opinionated:只支援 subagent 平台,沒有手動 fallback (+40 more)

### Community 32 - "Requirements"
Cohesion: 0.05
Nodes (37): Purpose, Requirement: Associate effort with the final physical set, Requirement: Confirm existing remote-day replacement, Requirement: Encode cardio with distance, Requirement: Encode duration-only cardio, Requirement: Preserve physical strength set boundaries, Requirement: Preserve the complete mixed training day, Requirement: Report expected and observed verification details (+29 more)

### Community 33 - "domain/planned_workout.py"
Cohesion: 0.23
Nodes (32): _array(), _fields(), _nonnegative_number(), _object(), _optional_date(), _optional_text(), _parse_block(), _parse_blocks() (+24 more)

### Community 34 - "Requirements"
Cohesion: 0.06
Nodes (31): Purpose, Requirement: Plan mutations before applying them, Requirement: Preserve the existing default synchronization scope, Requirement: Protect Garmin from downstream reconciliation, Requirement: Report partial outcomes without fictitious rollback, Requirement: Require explicit authorization to apply a plan, Requirement: Retry reconciliation idempotently, Requirement: Revalidate remote state before mutation (+23 more)

### Community 35 - "ADDED Requirements"
Cohesion: 0.06
Nodes (30): ADDED Requirements, Requirement: Plan mutations before applying them, Requirement: Preserve the existing default synchronization scope, Requirement: Protect Garmin from downstream reconciliation, Requirement: Report partial outcomes without fictitious rollback, Requirement: Require explicit authorization to apply a plan, Requirement: Retry reconciliation idempotently, Requirement: Revalidate remote state before mutation (+22 more)

### Community 36 - "planned_workout_from_dict"
Cohesion: 0.18
Nodes (29): planned_workout_from_dict(), Validate and normalize one versioned planned-workout document., project_planned_workout(), ProviderStepLimitError, Compile a validated plan without authentication or network I/O., Raised when a provider limit would require silently truncating steps., Any, Human-readable previews for planned Garmin workouts. (+21 more)

### Community 37 - "Requirements"
Cohesion: 0.07
Nodes (29): Purpose, Requirement: Authenticate without exposing Intervals credentials, Requirement: Delete only an exact authorized activity, Requirement: Disclose and preserve delete tombstones, Requirement: Inventory and read completed activities, Requirement: Match replicas deterministically, Requirement: Return actionable Intervals errors, Requirement: Support direct Intervals-only mutations (+21 more)

### Community 38 - "ADDED Requirements"
Cohesion: 0.07
Nodes (28): ADDED Requirements, Requirement: Authenticate without exposing Intervals credentials, Requirement: Delete only an exact authorized activity, Requirement: Disclose and preserve delete tombstones, Requirement: Inventory and read completed activities, Requirement: Match replicas deterministically, Requirement: Return actionable Intervals errors, Requirement: Support direct Intervals-only mutations (+20 more)

### Community 39 - "Requirements"
Cohesion: 0.07
Nodes (26): Purpose, Requirement: Distinguish imported strength evidence from completed activity, Requirement: Keep canonical activity separate from remote replicas, Requirement: Migrate existing Weight x Reps mappings safely, Requirement: Preserve effort at its observed scope, Requirement: Represent completed activities independently of providers, Requirement: Represent strength structure and load without provider leakage, Requirement: Resolve authority by field and retain provenance (+18 more)

### Community 40 - "ADDED Requirements"
Cohesion: 0.08
Nodes (25): ADDED Requirements, Requirement: Distinguish imported strength evidence from completed activity, Requirement: Keep canonical activity separate from remote replicas, Requirement: Migrate existing Weight x Reps mappings safely, Requirement: Preserve effort at its observed scope, Requirement: Represent completed activities independently of providers, Requirement: Represent strength structure and load without provider leakage, Requirement: Resolve authority by field and retain provenance (+17 more)

### Community 41 - "Requirements"
Cohesion: 0.08
Nodes (25): Purpose, Requirement: Canonical command-line interface, Requirement: Canonical installation is verifiable, Requirement: Canonical Python project identity, Requirement: Existing Training Sync configuration is preserved, Requirement: Operational interfaces use the canonical identity, Requirement: Synchronization behavior is preserved, Requirements (+17 more)

### Community 42 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 43 - "ADDED Requirements"
Cohesion: 0.08
Nodes (23): ADDED Requirements, Requirement: Canonical command-line interface, Requirement: Canonical installation is verifiable, Requirement: Canonical Python project identity, Requirement: Existing Training Sync configuration is preserved, Requirement: Operational interfaces use the canonical identity, Requirement: Synchronization behavior is preserved, Scenario: Clean installation verification (+15 more)

### Community 44 - "ExerciseResolutionRequired"
Cohesion: 0.19
Nodes (17): _candidate_matches(), _candidate_matches_for_names(), ExerciseCandidate, ExerciseResolutionRequired, RuntimeError, Resolve vault exercise names to Weight x Reps exercise IDs., resolve_exercise_ids(), test_create_if_missing_requires_full_catalog() (+9 more)

### Community 45 - "FakeManagementClient"
Cohesion: 0.25
Nodes (13): FakeManagementClient, plan(), remote_plan(), test_crud_mutations_record_operation_and_state_in_journal(), test_delete_reconciles_lost_response_by_reading_exact_template(), test_delete_requires_explicit_authorization_and_rejects_referenced_template(), test_delete_unreferenced_template_verifies_absence(), test_duplicate_creates_verified_new_template_without_touching_original() (+5 more)

### Community 46 - "Decisions"
Cohesion: 0.10
Nodes (19): 1. Adopt OpenSpec additively, 2. Use a global custom OpenSpec workflow profile, 3. Generate local adapters for Codex and OpenCode, 4. Pin Superpowers for OpenCode, 5. Keep `spec-driven` as the default and vendor the bridge, 6. Migrate one active change, 7. Split the feature contract into two capabilities, 8. Preflight before writes and do not roll back the daily on remote failure (+11 more)

### Community 47 - "ADDED Requirements"
Cohesion: 0.10
Nodes (19): ADDED Requirements, Requirement: Confirm existing remote-day replacement, Requirement: Encode cardio with distance, Requirement: Encode duration-only cardio, Requirement: Preserve the complete mixed training day, Requirement: Report expected and observed verification details, Requirement: Resolve every exercise before writes, Requirement: Retain unsupported Garmin metadata in comments (+11 more)

### Community 48 - "ADDED Requirements"
Cohesion: 0.10
Nodes (19): ADDED Requirements, Purpose, Requirement: Automatically group equivalent consecutive strength sets, Requirement: Preserve transition and terminal rests exactly, Requirement: Preview and verify grouped execution, Requirement: Safely manage supported grouped templates, Scenario: Bilbo and normal bench, Scenario: Combined unilateral sets (+11 more)

### Community 49 - "Requirements"
Cohesion: 0.11
Nodes (18): daily-multi-activity-sync Specification, Purpose, Requirement: Complete all preflight checks before writing, Requirement: Confirm non-empty daily replacement, Requirement: Fetch and stably order all activities, Requirement: Reject an empty Garmin day before writes, Requirement: Render one combined training section, Requirement: Require an existing daily note (+10 more)

### Community 50 - "GarminActivity"
Cohesion: 0.20
Nodes (16): GarminActivity, Normalized Garmin activity values used by synchronization., decode_activity(), _optional_float(), _optional_int(), Garmin payload decoding kept at the Garmin adapter boundary., Decode a Garmin activity-list payload into normalized activity values., _activity_comment() (+8 more)

### Community 51 - "File Structure"
Cohesion: 0.11
Nodes (17): Current Status, Execution Choice, Execution Status, File Structure, Spec Coverage Review, Task 10: Update README With Full Agent Flow, Task 11: Final Verification, Task 1: Complete Mapping Validation (+9 more)

### Community 52 - "File Structure"
Cohesion: 0.12
Nodes (16): File Structure, Final Verification, Self-Review Notes, Source References, Task 10: Manual OAuth and Real Write Verification, Task 11: Add `sync DATE` Orchestration Skeleton, Task 1: Add `training-sync` CLI Entry Point and Compatibility Wrapper, Task 2: Move Domain Models to `training_sync.domain` (+8 more)

### Community 53 - "Training Sync Weight x Reps Integration Design"
Cohesion: 0.12
Nodes (16): Architecture, CLI Shape, Context, Error Handling, Flow A: Garmin Activity Already Correct, Flow B: Strength Workout Comes From Fitbod Screenshots, Goals, JEditor Mapping (+8 more)

### Community 54 - "ADDED Requirements"
Cohesion: 0.12
Nodes (16): ADDED Requirements, Requirement: Complete all preflight checks before writing, Requirement: Confirm non-empty daily replacement, Requirement: Fetch and stably order all activities, Requirement: Reject an empty Garmin day before writes, Requirement: Render one combined training section, Requirement: Require an existing daily note, Requirement: Retain the daily on remote failure (+8 more)

### Community 55 - "Decisions"
Cohesion: 0.12
Nodes (16): 10. Migrate incrementally without persistent synchronization state, 1. Use a small canonical model and keep provider payloads in adapters, 2. Resolve authority per field and retain provenance, 3. Keep the Fitbod import as a pre-completion state, 4. Promote exercise mapping to a neutral local catalog, 5. Define seams by capability, not one universal CRUD interface, 6. Separate canonical reconciliation from provider-local editing, 7. Use a deterministic preview-and-apply plan (+8 more)

### Community 56 - "Usage"
Cohesion: 0.12
Nodes (16): 1. Pushing Strength Workouts to Garmin, 2. Fetching Activities from Garmin, 3. Fetching Body Weight from Garmin, 4. Reconciling a Day Across All Services, 5. Planned Garmin workouts, 6. Weight x Reps, 7. Intervals.icu, Authentication (+8 more)

### Community 57 - "Weight x Reps Exercise Resolution Design"
Cohesion: 0.12
Nodes (15): Agent-Oriented Output, Architecture, Candidate Matching, CLI Behavior, Context, Creating New Exercises, Error Handling, Goals (+7 more)

### Community 58 - "One-Day Sync and Cycling Support Design"
Cohesion: 0.12
Nodes (15): CLI Orchestration, Context, Daily Note Update, Garmin Activity Selection, Goals, Manual Verification, Non-Goals, One-Day Sync and Cycling Support Design (+7 more)

### Community 59 - "add-garmin-planned-workouts/design.md"
Cohesion: 0.12
Nodes (15): 1. Source-independent contract, 2. Explicit flattened steps first, 3. Additive commands and narrow modules, 4. Semantic verification and recoverable publication, Additional verification risks, Complete additive interface, Context, Decisions (+7 more)

### Community 60 - "Decisions"
Cohesion: 0.12
Nodes (15): Context, D1: Synchronize the complete Garmin day in stable order, D2: Produce one combined daily training section, D3: Complete every preflight before the first write, D4: Use one command-level confirmation contract, D5: Reconstruct and preserve the full Weight x Reps day, D6: Encode cardio with structured Weight x Reps fields, D7: Preserve non-native Garmin metrics in comments (+7 more)

### Community 61 - "Verification Report"
Cohesion: 0.13
Nodes (14): 1. Structural Validation (`openspec validate --all --json`), 2. Task Completion (`tasks.md`), 3. Delta Spec Sync State, 4. Design / Specs Coherence Spot Check, 5. Implementation Signal, 6. Front-Door Routing Leak Detector (warning, non-blocking), 7. Deferred Manual Dogfood vs Automated Test Equivalence, CRITICAL (+6 more)

### Community 62 - "ExerciseCatalog"
Cohesion: 0.25
Nodes (10): ExerciseCatalog, ExerciseIdentity, normalize_exercise_identity(), ProviderBinding, Stable local exercise identities and provider-specific bindings., load_exercise_catalog(), Read legacy Weight x Reps mappings without rewriting them., test_catalog_rejects_normalized_collisions() (+2 more)

### Community 63 - "test_planned_workout.py"
Cohesion: 0.25
Nodes (14): interval_plan(), parametrize, strength_plan(), test_boolean_is_not_accepted_as_numeric_value(), test_endurance_preserves_time_distance_targets_and_repeated_blocks(), test_invalid_planned_input_fails_with_field_specific_errors(), test_lap_warmup_and_explicit_null_final_rest_are_preserved(), test_malformed_plan_date_is_rejected_without_becoming_schedule_date() (+6 more)

### Community 64 - "Component Details"
Cohesion: 0.14
Nodes (13): 1. `pyproject.toml`, 2. `auth.py`, 3. `mapper.py`, 4. `commands/push.py`, 5. `commands/fetch.py`, 6. `cli.py`, Architecture & Structure, Component Details (+5 more)

### Community 65 - "Decision chain"
Cohesion: 0.14
Nodes (13): Approved design trade-offs, Background, Decision chain, Multi-Activity Day Sync Brainstorm Decision Log, Q1: Where should active requirements live?, Q2: How many Garmin activities should a day sync?, Q3: What authorizes local replacement?, Q4: What authorizes remote replacement? (+5 more)

### Community 66 - "Requirements"
Cohesion: 0.14
Nodes (13): local-configuration Specification, Purpose, Requirement: Centralize persistent local configuration, Requirement: Prefer non-empty environment overrides, Requirement: Separate local value classes, Requirement: Validate required vault configuration early, Requirements, Scenario: Environment override wins (+5 more)

### Community 67 - "ADDED Requirements"
Cohesion: 0.15
Nodes (12): ADDED Requirements, Requirement: Associate effort with the final physical set, Requirement: Preserve physical strength set boundaries, Requirement: Report the verified Weight x Reps journal URL, Scenario: Consolidated effort annotation is rejected, Scenario: Different repetitions remain separate physical rows, Scenario: Direct Weight x Reps push reports its journal entry, Scenario: Final single set receives RPE (+4 more)

### Community 68 - "Requirements"
Cohesion: 0.15
Nodes (12): direct-cli-install Specification, Purpose, Requirement: Distinguish editable and source-update semantics, Requirement: Keep development and operational workflows separate, Requirement: Preserve local and provider boundaries, Requirement: Provide a persistent direct operational command, Requirements, Scenario: A different checkout becomes operational source (+4 more)

### Community 69 - "Requirements"
Cohesion: 0.15
Nodes (12): Purpose, Requirement: Declare development dependencies separately, Requirement: Keep dependency setup separate from local and provider state, Requirement: Preserve Python compatibility in the locked project, Requirement: Provide locked development and test commands, Requirements, Scenario: Development environment includes pytest, Scenario: Fresh developer setup (+4 more)

### Community 70 - "PlannedWorkout"
Cohesion: 0.18
Nodes (10): parse_planned_workout(), PlannedWorkout, Normalized workout independent of its source and destination., Return the canonical representation excluding provenance., Alias for callers that prefer a parser-style name., build_garmin_workout_payload(), flatten_planned_workout(), Compatibility helper returning only the projected Garmin payload. (+2 more)

### Community 71 - "openspec-explore/SKILL.md"
Cohesion: 0.17
Nodes (11): Check for context, Ending Discovery, Guardrails, Handling Different Entry Points, OpenSpec Awareness, Planning a Change, The Stance, What You Don't Have To Do (+3 more)

### Community 72 - "2026-07-21-complete-training-sync-migration/design.md"
Cohesion: 0.17
Nodes (11): 1. Move Garmin behavior into a dedicated `training_sync.garmin` package, 2. Expose only the modern CLI contract, 3. Treat repository migration and machine cutover as separate gates, 4. Preserve current configuration state in place, 5. Keep historical records historically accurate, Context, Decisions, Goals / Non-Goals (+3 more)

### Community 73 - "ADDED Requirements"
Cohesion: 0.17
Nodes (11): ADDED Requirements, Requirement: Centralize persistent local configuration, Requirement: Prefer non-empty environment overrides, Requirement: Separate local value classes, Requirement: Validate required vault configuration early, Scenario: Environment override wins, Scenario: Local configuration files are resolved centrally, Scenario: Local file is used without an override (+3 more)

### Community 74 - "2026-07-31-centralize-local-configuration/design.md"
Cohesion: 0.18
Nodes (10): Context, D1: One persistent local configuration directory, D2: Environment override before local file, D3: Validate vault configuration before provider setup, D4: Classify values by sensitivity and purpose, Decisions, Goals / Non-Goals, Migration Plan (+2 more)

### Community 75 - "Verification Report"
Cohesion: 0.18
Nodes (10): 1. Structural Validation (`openspec validate --all --strict --json`), 2. Task Completion (`tasks.md`), 3. Delta Spec Sync State, 4. Design / Specs Coherence Spot Check, 5. Implementation Signal, 6. Front-Door Routing Leak Detector (warning, non-blocking), 7. Deferred Manual Dogfood vs Automated Test Equivalence, Evidence Commands (+2 more)

### Community 76 - "ADDED Requirements"
Cohesion: 0.18
Nodes (10): ADDED Requirements, Requirement: Distinguish editable and source-update semantics, Requirement: Keep development and operational workflows separate, Requirement: Preserve local and provider boundaries, Requirement: Provide a persistent direct operational command, Scenario: A different checkout becomes operational source, Scenario: Development remains lock-backed, Scenario: Direct command from another working directory (+2 more)

### Community 77 - "2026-07-31-migrate-to-uv/design.md"
Cohesion: 0.18
Nodes (10): Context, D1: Keep PEP 621 metadata and add a standard dev dependency group, D2: Commit uv's lockfile, D3: Use uv commands as the documented interface, D4: Preserve local configuration and provider boundaries, Decisions, Goals / Non-Goals, Migration Plan (+2 more)

### Community 78 - "ADDED Requirements"
Cohesion: 0.18
Nodes (10): ADDED Requirements, Requirement: Declare development dependencies separately, Requirement: Keep dependency setup separate from local and provider state, Requirement: Preserve Python compatibility in the locked project, Requirement: Provide locked development and test commands, Scenario: Development environment includes pytest, Scenario: Fresh developer setup, Scenario: Installation without credentials (+2 more)

### Community 79 - "Retrospective: add-one-day-multi-activity-sync"
Cohesion: 0.20
Nodes (9): 0. Evidence, 1. Wins, 2. Misses, 3. Plan deviations, 4. Skill / workflow compliance, 5. Surprises, 6. Promote candidates → long-term learning, Deliberately Skipped Skills (+1 more)

### Community 80 - "2026-07-31-add-canonical-activity-reconciliation/tasks.md"
Cohesion: 0.20
Nodes (9): 1. Baseline and Canonical Training Model, 2. Garmin and Strength Representation Migration, 3. Provider-Neutral Exercise Catalog, 4. Scoped Reconciliation Module, 5. Existing Adapter Compatibility, 6. Intervals Read and Identity, 7. Intervals Create, Update, Delete, and Verification, 8. CLI Composition and User-Facing Preview (+1 more)

### Community 81 - "Retrospective: centralize-local-configuration"
Cohesion: 0.20
Nodes (9): 0. Evidence, 1. Wins, 2. Misses, 3. Plan deviations, 4. Skill / workflow compliance, 5. Surprises, 6. Promote candidates → long-term learning, Deliberately Skipped Skills (+1 more)

### Community 82 - "2026-09-13-fix-weightxreps-set-semantics-and-sync-link/design.md"
Cohesion: 0.20
Nodes (9): Context, Decisions, Derive the journal URL from the authenticated session, Goals / Non-Goals, Migration Plan, Open Questions, Require final-set effort annotations, Risks / Trade-offs (+1 more)

### Community 83 - "Retrospective: <change-name>"
Cohesion: 0.20
Nodes (9): 0. Evidence, 1. Wins, 2. Misses, 3. Plan deviations, 4. Skill / workflow compliance, 5. Surprises, 6. Promote candidates → long-term learning, Deliberately Skipped Skills (+1 more)

### Community 84 - "templates/spec.md"
Cohesion: 0.20
Nodes (9): ADDED Requirements, MODIFIED Requirements, REMOVED Requirements, RENAMED Requirements, Requirement: <!-- requirement name -->, Requirement: <!-- 與既有 spec 中相同的 header -->, Requirement: <!-- 要刪除的 header，與既有 spec 完全相同 -->, Scenario: <!-- scenario name --> (+1 more)

### Community 85 - "Verification Report"
Cohesion: 0.20
Nodes (9): 1. Structural Validation (`openspec validate --all --json`), 2. Task Completion (`tasks.md`), 3. Delta Spec Sync State, 4. Design / Specs Coherence Spot Check, 5. Implementation Signal, 6. Front-Door Routing Leak Detector（warning,非阻塞）, 7. Deferred Manual Dogfood vs Automated Test Equivalence, Overall Decision (+1 more)

### Community 86 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 87 - "Verification Report"
Cohesion: 0.22
Nodes (8): 1. Structural validation, 2. Task completion, 3. uv behavior evidence, 4. Validation evidence, 5. Scope and safety, 6. Stable spec synchronization, Overall decision, Verification Report

### Community 88 - "Verification Report"
Cohesion: 0.22
Nodes (8): 1. Structural validation, 2. Task completion, 3. Implementation evidence, 4. Validation evidence, 5. Safety review, 6. Stable spec synchronization, Overall decision, Verification Report

### Community 89 - "Garmin Sync Modular Refactoring Implementation Plan"
Cohesion: 0.25
Nodes (7): Garmin Sync Modular Refactoring Implementation Plan, Task 1: Initialize Package Structure and Config, Task 2: Implement `mapper.py`, Task 3: Implement `auth.py`, Task 4: Implement `commands/push.py`, Task 5: Implement `commands/fetch.py`, Task 6: Implement `cli.py` and Clean Up Monolith

### Community 90 - "File Map"
Cohesion: 0.25
Nodes (7): File Map, Global Constraints, OpenSpec and Superpowers Integration Implementation Plan, Task 1: Configure global OpenSpec and OpenCode integration, Task 2: Initialize and version the OpenSpec project, Task 3: Migrate the active design into the bridge pilot, Task 4: Verify the completed integration without external writes

### Community 91 - "Garmin Sync Automation Design"
Cohesion: 0.25
Nodes (7): Architecture, Authentication & Session Management, Context, Garmin Sync Automation Design, Logic Flow, Script Interface, Updates to the AI Skill

### Community 92 - "Global Constraints"
Cohesion: 0.25
Nodes (7): Global Constraints, One-Day Multi-Activity Sync Implementation Plan, Task 1: CLI contract and orchestration preflight, Task 2: Daily multi-activity rendering, Task 3: Structured Weight x Reps cardio rows, Task 4: Remote reconciliation and verification, Task 5: Documentation and end-to-end verification

### Community 93 - "Retrospective: direct-cli-install"
Cohesion: 0.25
Nodes (7): 0. Evidence, 1. Wins, 2. Misses and corrections, 3. Plan deviations, 4. Skill / workflow compliance, 5. Promote candidates, Retrospective: direct-cli-install

### Community 94 - "Approaches considered"
Cohesion: 0.25
Nodes (7): A. Adopt uv project workflow with a checked-in lockfile (recommended), Approaches considered, B. Keep pip metadata and generate a requirements lock, C. Use uv only as an ephemeral runner, Current context, Design exploration: migrate-to-uv, Recorded recommendation

### Community 95 - "Retrospective: migrate-to-uv"
Cohesion: 0.25
Nodes (7): 0. Evidence, 1. Wins, 2. Misses and corrections, 3. Plan deviations, 4. Skill / workflow compliance, 5. Promote candidates, Retrospective: migrate-to-uv

### Community 96 - "superpowers-bridge Schema"
Cohesion: 0.25
Nodes (6): CLI cheat sheet, Related, superpowers-bridge Schema, Versioning, What problem does this solve?, Why a custom schema rather than modifying existing skills?

### Community 97 - "Apply phase walkthrough"
Cohesion: 0.25
Nodes (8): 0. Pre-flight — verify required Superpowers skills, 1. Workspace — `superpowers:using-git-worktrees`, 2. Executor — `superpowers:subagent-driven-development`, 3. Verification — `openspec-verify-change`, 4. Retrospective — `retrospective` artifact (recommended; per Entry & exit gates skip rules, trivial fixes may skip), 5. Archive — `openspec archive -y` (or `/opsx:archive`), 6. Completion — `superpowers:finishing-a-development-branch`, Apply phase walkthrough

### Community 98 - "templates/design.md"
Cohesion: 0.25
Nodes (7): Context, D1：<決策標題>, Decisions, Goals / Non-Goals, Migration Plan, Open Questions, Risks / Trade-offs

### Community 99 - "add-garmin-planned-workouts/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 100 - "ADDED Requirements"
Cohesion: 0.29
Nodes (6): ADDED Requirements, Purpose, Requirement: Keep planned and completed lifecycles distinct, Requirement: Rely on normal calendar synchronization, Scenario: Successful planned publication, Scenario: Workout scheduled successfully

### Community 101 - "add-garmin-planned-workouts/tasks.md"
Cohesion: 0.29
Nodes (6): 1. Portable planned-workout contract, 2. Executable preview and Garmin projection, 3. Verified publication and retry recovery, 4. Existing workout CRUD and calendar lifecycle, 5. CLI and usage contract, 6. Integration verification

### Community 102 - "2026-07-14-add-one-day-multi-activity-sync/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 103 - "2026-07-21-complete-training-sync-migration/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 104 - "2026-07-21-complete-training-sync-migration/tasks.md"
Cohesion: 0.29
Nodes (6): 1. Preflight and Isolation, 2. Canonical Garmin Package, 3. Distribution and CLI Cutover, 4. Current Documentation, 5. Repository Verification, 6. Explicit Machine Cutover Gate

### Community 105 - "2026-07-22-fix-weightxreps-full-catalog-lookup/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 106 - "2026-07-22-improve-weightxreps-graphql-errors/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 107 - "2026-07-31-add-canonical-activity-reconciliation/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 108 - "2026-07-31-centralize-local-configuration/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 109 - "Design: direct-cli-install"
Cohesion: 0.29
Nodes (6): Decision 1: Non-editable uv tool installation is the operational default, Decision 2: Editable installs are an explicit alternative, not the default, Decision 3: Updates are source-directed and explicit, Decision 4: Keep development and operation visibly separate, Design: direct-cli-install, Rejected alternatives

### Community 110 - "2026-07-31-migrate-to-uv/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 111 - "2026-09-13-fix-weightxreps-set-semantics-and-sync-link/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 112 - "group-garmin-strength-sets/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 113 - "Six design touches worth remembering"
Cohesion: 0.29
Nodes (7): 1. Skill-name PRECHECK (Layer 1 capability detection), 2. Schema-level vs prompt-level integration, 3. Transitive dependencies made explicit, 4. Opinionated: subagent platforms only, no manual fallback, 5. Evidence-based PRECHECK for verify and retrospective (Layer 2 capability detection), 6. verify and retrospective are time-mismatched artifacts (known limitation), Six design touches worth remembering

### Community 114 - "templates/proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 115 - "UnresolvedExercise"
Cohesion: 0.33
Nodes (4): UnresolvedExercise, test_sync_day_cli_prints_structured_exercise_resolution_error(), test_training_sync_weightxreps_exercises_resolve_prints_resolution_json(), test_training_sync_weightxreps_push_prints_resolution_json()

### Community 116 - "planned_json"
Cohesion: 0.29
Nodes (7): planned_json(), test_planned_workout_cli_reports_nonzero_failure_without_claiming_success(), test_planned_workout_cli_returns_nonzero_for_partial_lifecycle_result(), test_planned_workout_cli_wires_crud_and_calendar_commands(), test_planned_workout_create_only_authenticates_with_yes(), test_planned_workout_preview_has_file_and_stdin_parity(), test_planned_workout_preview_is_offline_and_does_not_need_vault_or_garmin()

### Community 117 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 118 - "Garmin Sync Python Script Implementation Plan"
Cohesion: 0.33
Nodes (5): Garmin Sync Python Script Implementation Plan, Task 1: Project Setup and JSON Parser (TDD), Task 2: Implement Playwright Session Manager, Task 3: Implement Garmin Connect UI Manipulation, Task 4: Update the `SKILL.md` File

### Community 119 - "Requirement: Preview the executable sequence"
Cohesion: 0.33
Nodes (6): Requirement: Preview the executable sequence, Scenario: Combined unilateral sets by default, Scenario: Explicit separate-side rounds, Scenario: Lap warm-up and final rest, Scenario: Last RDL set transitions to hip thrust, Scenario: Manual Bilbo set

### Community 120 - "2026-07-14-add-one-day-multi-activity-sync/tasks.md"
Cohesion: 0.33
Nodes (5): 1. CLI contract and orchestration preflight, 2. Daily multi-activity rendering, 3. Structured Weight x Reps cardio rows, 4. Remote reconciliation and verification, 5. Documentation and end-to-end verification

### Community 121 - "Global Constraints"
Cohesion: 0.33
Nodes (5): Direct CLI Installation Implementation Plan, Global Constraints, Task 1: Record and validate uv tool behavior, Task 2: Update the operational documentation, Task 3: Validate, archive, and deliver the documentation change

### Community 122 - "Global Constraints"
Cohesion: 0.33
Nodes (5): Global Constraints, Migrate Training Sync to uv Implementation Plan, Task 1: Project metadata and lockfile, Task 2: uv developer and test documentation, Task 3: Final verification and safety review

### Community 123 - "group-garmin-strength-sets/design.md"
Cohesion: 0.33
Nodes (5): Context, Decisions, Goals / Non-Goals, Migration Plan, Risks / Trade-offs

### Community 124 - "group-garmin-strength-sets/tasks.md"
Cohesion: 0.33
Nodes (5): 1. Decode and verify repeat semantics, 2. Generate compact strength payloads, 3. Publication and recovery, 4. Supported template management, 5. Integration and delivery

### Community 125 - "Workflow routing (read on session start)"
Cohesion: 0.33
Nodes (5): Entry routing, Front-door anti-patterns (don't do), Verbal brainstorm → opsx promotion criteria, When NOT to use opsx (direct PR), Workflow routing (read on session start)

### Community 126 - "變更工作流(Claude Code 啟動先讀)"
Cohesion: 0.33
Nodes (5): Front-door 反模式(別做), Verbal brainstorm 升級到 opsx 的 5 條判準, 何時**不**走 opsx(直接 PR), 入口分流, 變更工作流(Claude Code 啟動先讀)

### Community 127 - "Requirement: Represent multideporte interval prescriptions"
Cohesion: 0.40
Nodes (5): Requirement: Represent multideporte interval prescriptions, Scenario: Distance-based running, Scenario: Indoor cycling sequence, Scenario: Running power intervals, Scenario: Unsupported or unresolved target

### Community 128 - "Requirement: Update and duplicate workouts safely"
Cohesion: 0.40
Nodes (5): Requirement: Update and duplicate workouts safely, Scenario: Concurrent remote edit, Scenario: Duplicate template, Scenario: Existing workout load edit, Scenario: Unsupported structure

### Community 129 - "2026-07-22-fix-weightxreps-full-catalog-lookup/design.md"
Cohesion: 0.40
Nodes (4): Context, Decisions, Goals / Non-Goals, Risks / Trade-offs

### Community 130 - "Requirement: Resolve exercises using the complete catalog"
Cohesion: 0.40
Nodes (4): ADDED Requirements, Requirement: Resolve exercises using the complete catalog, Scenario: Complete catalog lookup fails, Scenario: Configured user enables complete catalog lookup

### Community 131 - "2026-07-22-improve-weightxreps-graphql-errors/design.md"
Cohesion: 0.40
Nodes (4): Context, Decisions, Goals / Non-Goals, Risks / Trade-offs

### Community 132 - "Requirement: Surface Weight x Reps GraphQL errors"
Cohesion: 0.40
Nodes (4): ADDED Requirements, Requirement: Surface Weight x Reps GraphQL errors, Scenario: Failed HTTP response contains GraphQL errors, Scenario: Failed HTTP response lacks GraphQL errors

### Community 133 - "Retrospective design capture: centralize-local-configuration"
Cohesion: 0.40
Nodes (4): Evidence boundary, Observed problem, Recorded decisions, Retrospective design capture: centralize-local-configuration

### Community 134 - "Proposal: direct-cli-install"
Cohesion: 0.40
Nodes (4): Proposal: direct-cli-install, Scope, What changes, Why

### Community 135 - "Workflow & integration"
Cohesion: 0.40
Nodes (5): Artifact DAG, Lifecycle (apply orchestration + timing notes), Output redirection, Seven Superpowers touchpoints, Workflow & integration

### Community 136 - "Repository instructions"
Cohesion: 0.50
Nodes (3): Branch naming, graphify, Repository instructions

### Community 137 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 138 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 139 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 140 - "Planned Garmin device smoke test"
Cohesion: 0.50
Nodes (3): Evidence levels, Fresh test procedure, Planned Garmin device smoke test

### Community 141 - "Requirement: Manage calendar occurrences independently"
Cohesion: 0.50
Nodes (4): Requirement: Manage calendar occurrences independently, Scenario: Move to another date, Scenario: Remove only the occurrence, Scenario: Repeated schedule request

### Community 142 - "Requirement: Verify creation and scheduling independently"
Cohesion: 0.50
Nodes (4): Requirement: Verify creation and scheduling independently, Scenario: Calendar failure, Scenario: Date independent of source, Scenario: Saved rest mismatch

### Community 143 - "2026-07-22-fix-weightxreps-full-catalog-lookup/tasks.md"
Cohesion: 0.50
Nodes (3): 1. Regression Coverage, 2. Client Compatibility Fix, 3. Verification

### Community 144 - "2026-07-22-improve-weightxreps-graphql-errors/tasks.md"
Cohesion: 0.50
Nodes (3): 1. Regression Coverage, 2. Client Error Handling, 3. Verification

### Community 145 - "Local Configuration Retrospective Plan"
Cohesion: 0.50
Nodes (3): Local Configuration Retrospective Plan, Task 1: Reconstruct implementation evidence, Task 2: Create and validate OpenSpec artifacts

### Community 146 - "2026-07-31-direct-cli-install/tasks.md"
Cohesion: 0.50
Nodes (3): 1. uv tool behavior evidence, 2. Operational documentation, 3. Delivery

### Community 147 - "2026-07-31-migrate-to-uv/tasks.md"
Cohesion: 0.50
Nodes (3): 1. Project dependency and lock setup, 2. Developer documentation, 3. Final safety validation

### Community 148 - "2026-09-13-fix-weightxreps-set-semantics-and-sync-link/tasks.md"
Cohesion: 0.50
Nodes (3): 1. Regression Coverage, 2. Weight x Reps Implementation, 3. Verification and Handoff

### Community 149 - "Design decisions worth knowing"
Cohesion: 0.50
Nodes (4): Design decisions worth knowing, Fallback strategy, Why `brainstorm` is an artifact, not a hook, Why `plan` is separate from `tasks`

### Community 150 - "Entry & exit gates"
Cohesion: 0.50
Nodes (4): Entry & exit gates, Front-door anti-patterns, When NOT to enter the schema (direct PR), When verbal brainstorming should be promoted to a change

### Community 151 - "Usage"
Cohesion: 0.50
Nodes (4): Quick flow (recommended), Step-by-step flow, Switching back to spec-driven, Usage

### Community 152 - "Upgrading an existing install"
Cohesion: 0.50
Nodes (4): Upgrade Method 1: Claude Code one-shot prompt (recommended), Upgrade Method 2: Manual bash, Upgrading an existing install, What the upgrade overwrites

### Community 155 - "Requirement: Accept source-independent planned input"
Cohesion: 0.67
Nodes (3): Requirement: Accept source-independent planned input, Scenario: Equivalent sources, Scenario: Invalid input

### Community 156 - "Requirement: Delete only exact authorized templates"
Cohesion: 0.67
Nodes (3): Requirement: Delete only exact authorized templates, Scenario: Referenced template deletion, Scenario: Unscheduled template deletion

### Community 157 - "Requirement: Inventory existing and application-created resources"
Cohesion: 0.67
Nodes (3): Requirement: Inventory existing and application-created resources, Scenario: Manually created workout, Scenario: Multiple entries on one date

### Community 158 - "Requirement: Isolate single-date prescription changes"
Cohesion: 0.67
Nodes (3): Requirement: Isolate single-date prescription changes, Scenario: Change tomorrow only, Scenario: Replacement scheduled but original removal fails

### Community 159 - "Requirement: Preserve exercise identity and load semantics"
Cohesion: 0.67
Nodes (3): Requirement: Preserve exercise identity and load semantics, Scenario: Explicit substitute, Scenario: Unmapped exercise

### Community 160 - "Requirement: Recover without blind duplication"
Cohesion: 0.67
Nodes (3): Requirement: Recover without blind duplication, Scenario: Lost upload response, Scenario: Retry after calendar failure

### Community 161 - "Requirement: Verify all mutations and recover partial outcomes"
Cohesion: 0.67
Nodes (3): Requirement: Verify all mutations and recover partial outcomes, Scenario: Lost deletion response, Scenario: Target mismatch after update

### Community 164 - "Compatibility"
Cohesion: 0.67
Nodes (3): Compatibility, How this is checked, Known breaking changes

### Community 165 - "Install"
Cohesion: 0.67
Nodes (3): Install, Method 1: Claude Code one-shot prompt (recommended), Method 2: Manual bash (CI / non-Claude environments)

## Knowledge Gaps
- **879 isolated node(s):** `training-sync`, `The Stance`, `Planning a Change`, `What You Might Do`, `Check for context` (+874 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1216 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WeightxRepsClient` connect `WeightxRepsClient` to `cli.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `planned_workout_from_dict()` connect `planned_workout_from_dict` to `domain/planned_workout.py`, `PlannedWorkout`, `domain/__init__.py`, `cli.py`, `FakeManagementClient`, `manage_planned_workouts.py`, `publish_workout.py`, `planned_workouts.py`, `test_planned_workout.py`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `project_planned_workout()` connect `planned_workout_from_dict` to `import_strength.py`, `PlannedWorkout`, `cli.py`, `FakeManagementClient`, `manage_planned_workouts.py`, `publish_workout.py`, `planned_workouts.py`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `project_planned_workout()` (e.g. with `planned_workouts.py` and `PlannedWorkout`) actually correct?**
  _`project_planned_workout()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `training-sync`, `The Stance`, `Planning a Change` to the rest of the system?**
  _879 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `weightxreps/exercise_mapping.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13090418353576247 - nodes in this community are weakly interconnected._
- **Should `WeightxRepsClient` be split into smaller, more focused modules?**
  _Cohesion score 0.0716297786720322 - nodes in this community are weakly interconnected._