# Graph Report - training-sync  (2026-09-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 725 nodes · 1870 edges · 29 communities (17 shown, 9 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 265 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d69b60d5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 28

## God Nodes (most connected - your core abstractions)
1. `preflight_sync_day()` - 46 edges
2. `activity()` - 35 edges
3. `ExerciseMapping` - 34 edges
4. `fake_dependencies()` - 34 edges
5. `WeightxRepsClient` - 32 edges
6. `ParsedSetLine` - 28 edges
7. `ParsedTrainingDay` - 28 edges
8. `IntervalsClient` - 28 edges
9. `ExerciseResolutionRequired` - 24 edges
10. `ParsedExercise` - 22 edges

## Surprising Connections (you probably didn't know these)
- `test_weightxreps_parser_values_are_canonical_domain_values()` --uses--> `ParsedTrainingDay`  [INFERRED]
  tests/test_strength_workout_plan.py → src/training_sync/domain/training.py
- `test_preview_weightxreps_day_uses_remote_exercise_ids()` --indirect_call--> `vault_root()`  [INFERRED]
  tests/test_training_sync_cli.py → src/training_sync/config.py
- `test_rendered_supported_aliases_round_trip_to_canonical_preview_rows_and_skip_strength()` --uses--> `GarminActivity`  [INFERRED]
  tests/test_weightxreps_preview.py → src/training_sync/domain/garmin_activity.py
- `test_build_complete_training_day_preserves_only_strength_from_prior_day()` --calls--> `ParsedSetLine`  [INFERRED]
  tests/test_use_case_sync_day.py → src/training_sync/domain/training.py
- `test_build_complete_training_day_treats_strength_as_local_only_and_preserves_strength()` --calls--> `ParsedSetLine`  [INFERRED]
  tests/test_use_case_sync_day.py → src/training_sync/domain/training.py

## Import Cycles
- None detected.

## Communities (29 total, 9 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (71): ExerciseCatalog, ExerciseIdentity, normalize_exercise_identity(), ProviderBinding, Stable local exercise identities and provider-specific bindings., _extract_text_blocks(), load_weightxreps_day_from_vault(), preview_weightxreps_day_from_vault() (+63 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (65): GarminActivity, Normalized Garmin activity values used by synchronization., decode_activity(), _optional_float(), _optional_int(), Garmin payload decoding kept at the Garmin adapter boundary., Decode a Garmin activity-list payload into normalized activity values., _activity_comment() (+57 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (49): build_journal_url(), _default_date_from_rows(), _empty_comment_default(), _normalize_expected_blocks(), _normalize_expected_set(), _normalize_observed_blocks(), _normalize_observed_set(), Any (+41 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (32): BinaryIO, IntervalsActivity, IntervalsClient, IntervalsError, IntervalsNotFoundError, IntervalsUnsupportedUpdateError, Any, RuntimeError (+24 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (41): Any, Strength workout domain objects and input normalization., Normalize Fitbod-like workout data into a strength workout., strength_workout_from_dict(), StrengthExercise, StrengthSet, StrengthWorkout, get_mapping() (+33 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (39): ParsedExercise, ParsedSetLine, ParsedTrainingDay, _parse_duration_ms(), _parse_exercise_block(), _parse_set_line(), parse_weightxreps_text(), finish_exercise() (+31 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (16): TokenSet, ExerciseResolutionRequired, RuntimeError, parametrize, test_intervals_list_and_show_are_read_only(), test_intervals_update_is_preview_by_default_and_apply_is_verified(), test_preview_weightxreps_day_uses_remote_exercise_ids(), test_push_weightxreps_day_cli_passes_explicit_user_id() (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (29): date, format_weight_tag(), Body-weight domain objects., WeightReading, ActivityMetric, Normalized training log entries., TrainingEntry, _body_weight_tag() (+21 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (23): OperationKind, StrEnum, Values used to preview and safely apply scoped reconciliation., ReconciliationOperation, ReconciliationPlan, ReconciliationResult, SyncScope, TargetResult (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.14
Nodes (24): datetime, Pure training-sync domain objects., CompletedActivity, EffortObservation, EffortScope, Load, LoadKind, promote_verified_strength_import() (+16 more)

### Community 10 - "Community 10"
Cohesion: 0.19
Nodes (18): push_weightxreps_day(), Path, FakeWeightxRepsClient, Path, test_push_weightxreps_day_creates_explicitly_mapped_new_exercise(), test_push_weightxreps_day_does_not_create_with_partial_jeditor_catalog(), test_push_weightxreps_day_does_not_write_unresolved_exercises(), test_push_weightxreps_day_prefers_explicit_exercise_ids_over_catalog() (+10 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (20): auth_weightxreps_cli(), build_weightxreps_client(), refresh_token(), Path, _wait_for_weightxreps_callback(), build_authorization_url(), exchange_code_for_tokens(), generate_pkce_pair() (+12 more)

### Community 12 - "Community 12"
Cohesion: 0.19
Nodes (23): _configured_vault_root(), _exit_with_resolution_payload(), preview_weightxreps_day(), push_weightxreps_day_cli(), sync_day_cli(), _weightxreps_url(), config_dir(), garmin_token_path() (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.15
Nodes (21): ActivityClassification, classify_activity_type(), Shared Garmin activity classification for rendering and Weight x Reps., _activity_tag(), _duration_text(), _metric_text(), _pace_text(), Pure rendering for ordered Garmin activities in a daily training section. (+13 more)

### Community 14 - "Community 14"
Cohesion: 0.15
Nodes (17): daily_note_path(), Path, Daily note path helpers., extract_training_section(), Read and update the ## 🏃 Training section in daily notes., replace_training_section(), _section_bounds(), training_section_has_content() (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.23
Nodes (15): ArgumentParser, Namespace, _add_modern_subcommands(), build_intervals_client(), _build_parser(), _dispatch(), _distribution_version(), intervals_cli() (+7 more)

### Community 16 - "Community 16"
Cohesion: 0.20
Nodes (4): Training synchronization across Garmin, Obsidian, and Weight x Reps., parametrize, test_vault_root_rejects_relative_configuration(), test_vault_root_requires_configuration_when_both_sources_are_absent()

## Knowledge Gaps
- **1 isolated node(s):** `training-sync`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 176 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WeightxRepsClient` connect `Community 2` to `Community 11`, `Community 15`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `IntervalsClient` connect `Community 3` to `Community 15`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `preflight_sync_day()` connect `Community 1` to `Community 0`, `Community 13`, `Community 5`, `Community 14`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `ExerciseMapping` (e.g. with `SyncDependencies` and `preview_weightxreps_day_from_vault()`) actually correct?**
  _`ExerciseMapping` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `WeightxRepsClient` (e.g. with `test_current_username_reads_authenticated_weightxreps_user()` and `test_day_has_content_uses_jeditor_data()`) actually correct?**
  _`WeightxRepsClient` has 17 INFERRED edges - model-reasoned connections that need verification._
- **What connects `training-sync` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05987703822507351 - nodes in this community are weakly interconnected._