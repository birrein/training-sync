## Context

Training Sync already coordinates Garmin Connect, an existing Obsidian daily note, and Weight x Reps. Its original architecture intentionally used modular use cases and concrete adapters without introducing abstract interfaces before real variation existed. That variation now exists: Intervals.icu needs full activity lifecycle support, TrainingPeaks is expected later, and the user needs to choose exactly which platforms a mutation affects.

The current domain is split across overlapping provider-shaped representations:

- `GarminActivity` mixes normalized activity values with Garmin payload decoding.
- `ParsedTrainingDay`, `ParsedExercise`, and `ParsedSetLine` live in a Weight x Reps renderer but are consumed by use cases and clients.
- exercise identity is centered on `weightxreps_name` and `weightxreps_id`;
- `sync_day` knows concrete provider behavior and has no representation for remote replicas, exact target scope, or per-target lifecycle results.

Garmin remains authoritative for completed objective execution after correction and verification. The vault remains authoritative for subjective context such as exercise-level RIR, global session RPE, Feel, and recovery. Weight x Reps remains a structured strength reference and reconciled destination. Fitbod screenshots remain a supported import input: they are converted into a strength import, applied to Garmin, verified there, and only then treated as a completed activity.

Intervals.icu's current published contract exposes activity list, get, upload, update, and delete operations. Its activity update endpoint does not support Strava-sourced activities. Deleting an activity imported from an external service such as Garmin creates a tombstone that prevents automatic re-import, while deleting an application upload removes it without a tombstone.

## Goals / Non-Goals

**Goals:**

- Establish a provider-neutral canonical model that covers completed cardio and strength activity data without becoming a superset of every remote payload.
- Preserve the Fitbod screenshot to verified Garmin to downstream workflow.
- Preserve effort at its observed scope: set, exercise, or session.
- Give exercises stable local identities with provider-specific mappings.
- Allow reconciliation or direct mutation of one platform, an explicit subset, or all configured destinations.
- Centralize deterministic planning, confirmation, conflict handling, partial results, and read-back verification.
- Implement safe Intervals.icu read, create, update, and delete behavior.
- Keep existing Garmin, vault, and Weight x Reps behavior and tests valid while migrating their implementations behind the new seams.

**Non-Goals:**

- Add TrainingPeaks access or assume unsupported TrainingPeaks operations.
- Add a database, event store, background worker, webhook receiver, or continuous synchronization.
- Implement every possible new Garmin or vault lifecycle operation in this change.
- Normalize dense telemetry streams into the canonical model.
- Treat Fitbod as a completed-activity source or add a Fitbod integration.
- Hard-code the user's Fitbod subscription date into product behavior.
- Automatically mutate every configured platform.
- Roll back already verified remote writes when another independent target fails.

## Decisions

### 1. Use a small canonical model and keep provider payloads in adapters

The domain will introduce provider-neutral values centered on:

- `CompletedActivity`: stable activity identity, title, type, local start, elapsed and active duration, objective summaries, optional strength content, provenance, and source artifact reference;
- `StrengthWorkoutImport`: extracted but not yet Garmin-verified strength evidence;
- `StrengthExercise` and `StrengthSet`: stable exercise identity, order, set role, repetitions, and a structured load that can represent mass, bodyweight, assistance, resistance, or non-load primer work;
- `EffortObservation`: RIR or RPE with set, exercise, or session scope, provenance, and optional derivation metadata;
- `ActivityReplica`: provider, remote ID, external ID, source type, observed fingerprint, and lifecycle state;
- `SourceArtifact`: an opaque reference to the original FIT, TCX, GPX, ZIP, or provider payload when exact telemetry must be preserved.

Dense heart-rate or GPS samples and provider-only analysis fields remain inside source artifacts or adapters. This avoids a giant canonical object while preserving the original file needed for upload, merge, or verification.

Alternative considered: retain `GarminActivity` as the shared model. Rejected because Garmin decoding and provider-neutral semantics would remain coupled and every new destination would depend on Garmin field names.

### 2. Resolve authority per field and retain provenance

Authority is not one flat provider precedence:

1. an explicit current user correction wins;
2. a Garmin activity that has been corrected and read back is authoritative for whether the activity occurred and for objective execution;
3. the vault is authoritative for subjective context and effort recorded there;
4. verified Weight x Reps data can fill missing structured strength detail but does not silently override corrected Garmin data;
5. destination replicas never silently become canonical.

Projected values retain their origin and any derivation. For example, exercise-level `RIR 1` remains an exercise-scoped RIR observation; the Weight x Reps adapter can derive `RPE 9` for compatible rows without replacing the original observation.

### 3. Keep the Fitbod import as a pre-completion state

Fitbod screenshots produce `StrengthWorkoutImport`, not `CompletedActivity`. The Garmin adapter applies the import to the recorded activity, preserving telemetry, and reads the result back. Only a verified result becomes canonical completed activity data.

If Garmin recording is split, merge or replacement remains an explicit Garmin use case. It creates and verifies the corrected activity before deleting authorized originals. Downstream reconciliation never deletes Garmin.

### 4. Promote exercise mapping to a neutral local catalog

The catalog will use a stable local key and preferred name, aliases, and provider bindings. A conceptual entry is:

```toml
[[exercises]]
key = "chin_up"
name = "Chin Up"
aliases = ["Chin-up", "Dominada supina", "Loop Band Chin Up"]

[exercises.providers.weightxreps]
id = 123
name = "Chin Up"
```

Provider IDs and names no longer define canonical identity. Normalized duplicate keys, preferred names, or aliases that point to different exercises remain hard errors.

The migration reads the existing Weight x Reps-centered TOML format, converts it to the neutral in-memory representation, and writes the new format only through an explicit mapping mutation. Existing files are backed up before conversion.

### 5. Define seams by capability, not one universal CRUD interface

Adapters can satisfy only the interfaces they support:

- inventory and read;
- create or upload;
- partial metadata update or replacement;
- delete;
- read-back verification;
- source-artifact download.

The reconciliation module asks for the needed capabilities and fails before mutation when a selected adapter cannot perform the requested operation. This keeps provider restrictions local to each adapter and avoids no-op or fake CRUD methods.

### 6. Separate canonical reconciliation from provider-local editing

Two use cases share the same planning and safety module:

- canonical reconciliation projects one canonical activity or day into an exact `SyncScope`;
- provider-local editing changes one replica without propagating to other platforms.

Explicitly named platforms form the target set. `all` selects all configured compatible targets. Unselected platforms are never mutated. Existing `sync DATE` behavior remains the compatibility default for the vault and Weight x Reps; adding a configured Intervals.icu adapter does not silently expand that command's targets.

A later full reconciliation detects a provider-local difference and displays the proposed overwrite as a conflict. It never silently erases an isolated edit.

### 7. Use a deterministic preview-and-apply plan

`ReconciliationPlan` contains:

- canonical source and provenance summary;
- exact selected targets;
- ordered create, update, delete, or no-op operations;
- remote IDs and human-readable activity identity;
- reasons for matches, conflicts, and duplicate classification;
- destructive consequences such as an Intervals.icu tombstone;
- an observed remote fingerprint for each mutation target.

Preview is the default. Explicit confirmation authorizes exactly the displayed plan. Immediately before each mutation, the adapter re-reads or validates the expected fingerprint. A changed remote state fails that target and requires a fresh plan.

### 8. Report partial results instead of pretending there is a distributed transaction

All preflight validation that can be performed without mutation happens before the first write. Targets are then applied and verified independently. Each result is `verified`, `failed`, or `not_attempted`, with remote identity and actionable error detail.

A verified write is not rolled back because another provider fails. Retry re-plans current state and targets only failed or pending destinations, making successful operations idempotent.

### 9. Implement the published Intervals.icu activity contract

The Intervals adapter will:

- list summaries for a bounded local date range and get a specific activity;
- download the original file when needed;
- upload Garmin source artifacts with the canonical Garmin ID as `external_id`;
- update only changed supported fields using the activity update endpoint;
- reject update plans for Strava-sourced activities before mutation;
- delete an exact remote ID only after explicit authorization;
- disclose when deletion creates a tombstone and verify the resulting deleted or absent state;
- never remove tombstones automatically;
- authenticate with a personal API key kept in local secret configuration and redact credentials from output.

Replica matching prefers exact provider identity and `external_id`. A fallback match can use normalized local start, compatible activity type, and objective duration or distance only when it produces one candidate. Multiple candidates remain an explicit conflict; they are not automatically deleted.

The contract was verified on 2026-07-27 against:

- `https://intervals.icu/api/v1/docs`
- `https://www.intervals.icu/features/open-api/`
- `https://forum.intervals.icu/t/intervals-icu-api-integration-cookbook/80090`
- `https://forum.intervals.icu/t/delete-activity-tombstones/130079`

### 10. Migrate incrementally without persistent synchronization state

The first slice moves existing shared values into the canonical domain while keeping compatibility adapters and current commands green. It then introduces planning and scoped execution, followed by the Intervals adapter.

Remote state is reconstructed on demand. Preview plans exist only for the command invocation and are revalidated before apply. A database is deferred until a concrete need such as background synchronization, durable audit history, or queued retries appears.

Alternative considered: introduce a persistent event store immediately. Rejected because it adds migrations and operational state without being necessary for explicit user-driven synchronization.

## Risks / Trade-offs

- [Existing models leak through many modules] → Migrate one behavior-preserving slice at a time and keep compatibility tests around current CLI, vault, and Weight x Reps flows.
- [Exercise mapping conversion could lose user configuration] → Support dual-read, validate collisions before conversion, create a timestamped backup, and verify a read-back of the new format.
- [Fallback activity matching can select the wrong replica] → Require one candidate, show match evidence, and never delete on fallback ambiguity.
- [A remote platform changes between preview and apply] → Compare the observed fingerprint immediately before mutation and require re-planning on mismatch.
- [Multi-target synchronization partially succeeds] → Return per-target results and make retries idempotent instead of claiming atomic rollback.
- [Deleting a Garmin-sourced Intervals activity prevents re-import] → Show the tombstone consequence in preview and never remove a tombstone automatically.
- [Intervals.icu changes its public contract] → Keep HTTP details inside the adapter and cover the published payload shapes with focused contract fixtures.
- [The canonical model grows into a provider superset] → Admit only stable cross-provider concepts; keep dense telemetry and provider-only analysis in source artifacts and adapter payloads.
- [The OpenSpec config still contains a rule for the inactive `plan` artifact] → Treat the CLI warning as repository tooling debt and correct it separately without changing this feature's behavior.

## Migration Plan

1. Add canonical domain values and mapping tests without changing the current CLI.
2. Move Garmin payload decoding out of canonical values and adapt existing Garmin rendering and strength-import tests.
3. Move parsed strength values out of the Weight x Reps renderer and adapt vault and Weight x Reps clients.
4. Add the neutral exercise catalog with backward-compatible reading and explicit safe conversion.
5. Introduce reconciliation planning, exact scope, capability-aware adapters, and per-target results behind existing use cases.
6. Preserve current `sync DATE` behavior and prove the existing full test suite remains green.
7. Add Intervals configuration and read-only inventory.
8. Add upload, update, delete, tombstone disclosure, and independent read-back verification test-first.
9. Add scoped CLI entry points and end-to-end dry-run tests.
10. Run strict OpenSpec validation, the full Python suite, packaging smoke tests, and read-only live Intervals verification before any optional live mutation test.

Rollback is a code rollback plus restoration of the prior exercise mapping backup if conversion occurred. No persistent database migration is required. Remote mutations are never part of automated tests; any live operation requires its own preview, authorization, and read-back.

## Open Questions

- TrainingPeaks access and exact completed-activity lifecycle capabilities will be researched in its own change.
- New generic Garmin merge or vault-delete commands will be specified only when a concrete use case requires them.
- Durable audit history or queued retry state will be reconsidered only if explicit user-driven reconciliation becomes insufficient.
