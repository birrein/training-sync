## Context

See proposal.md for motivation. `garmin/import_strength.py` updates sets on an existing completed activity. `domain/strength_workout.py` models repetitions and kilograms but lacks rest, side and termination semantics. `garmin/auth.py` already supplies authentication, and `garmin/exercise_mapping.py` supplies names but currently falls back to UNKNOWN for unmatched exercises. Planned publication needs stricter validation without changing that legacy behavior.

The live experiment verified upload_workout, get_workout_by_id, schedule_workout and calendar read-back. It also demonstrated that a repeat group's skipLastRestStep changes the actual execution sequence. An accepted HTTP response is insufficient validation.

## Goals / Non-Goals

Goals: a reusable Python API and CLI for strength, cycling/indoor cycling and running; deterministic preview; explicit load, side, rest and intensity semantics; verified CRUD for new/existing workouts and independent calendar operations.

Non-goals: interpreting screenshots or arbitrary prose in the CLI, reading a vault heading, prescribing training or injury rehabilitation, editing completed activities, unrequested replacement/deletion, explicit device push, or claiming device receipt. Normal Garmin Connect calendar synchronization handles device download.

## Decisions

### 1. Source-independent contract

Add `domain/planned_workout.py` with strict parsing and a public model. JSON comes from a file or stdin (`-`). The assistant translates user intent into this document, asking about genuinely missing training choices. Source metadata is optional, free-form provenance retained locally, not an execution dependency and not uploaded verbatim to Garmin.

The optional `garmin_name` field belongs to this assistant-prepared JSON; it is
not read from a vault or returned by Garmin. It is allowed only when the user
explicitly chooses a provider substitute, such as preserving `Dragon Flag` as
the original name while executing the catalog entry `Reverse Crunch on a
Bench`. The resolver validates that human-readable catalog name and keeps both
names in preview/description. When `garmin_name` is absent, resolution keeps
the legacy precedence of an explicit mapping/alias over an exact catalog
entry. A normalized collision between mappings, aliases or catalog entries is
an error; no automatic substitution is introduced.

V1 example (abbreviated session containing one exercise):

```json
{
  "schema_version": 1,
  "key": "lower-body-2-2026-09-13",
  "name": "Lower Body 2",
  "sport": "strength_training",
  "warmup": {"until": "lap", "description": "8–10 min"},
  "exercises": [
    {
      "name": "Romanian Deadlift",
      "sets": [
        {"reps": 10, "load": {"kind": "mass", "kg": 83, "basis": "total"}},
        {"reps": 10, "load": {"kind": "mass", "kg": 83, "basis": "total"}},
        {"reps": 10, "load": {"kind": "mass", "kg": 83, "basis": "total"}}
      ],
      "rest_between_sets": {"until": "time", "seconds": 165},
      "rest_after_exercise": {"until": "time", "seconds": 165}
    }
  ]
}
```

Termination supports time (positive finite seconds) or lap. Sets support positive integer reps, timed duration or manual lap, never conflicting termination fields; Bilbo can end by lap without an invented rep target. Loads support mass with nonnegative finite kg and basis total/per_hand, or explicit bodyweight; assistance/bands are rejected in v1 rather than guessed. Explicit per-hand loads retain the prescribed number and basis in Garmin step descriptions and preview. Ranges must be resolved before publication; do not silently choose midpoints. Unknown fields, malformed dates, booleans used as numbers, empty exercises and unsupported versions fail before authentication.

Unilateral exercises default to combined sides: one step per set, repetitions prescribed per side, an instruction to complete both sides before ending the set, and rest after both. Do not double repetitions, loads or recorded steps, and do not imply automatic side detection. Explicit separate-side mode may specify `sides: ["left", "right"]` and `rest_between_sides`; it is never inferred. Rest fields are required where applicable; null explicitly means no rest. `rest_after_exercise` also applies when the exercise is last, so final-rest policy is visible rather than hidden in compiler defaults.

Alternative: add daily/Chat/Fitbod parsers to the CLI. Rejected for v1 because source formats change and interpretation already happens in the assistant. Alternative: expose raw Garmin JSON. Rejected because that would require every caller to understand provider execution flags.

### 2. Explicit flattened steps first

`garmin/planned_workouts.py` compiles to a flat sequence of ExecutableStepDTO entries with consecutive stepOrder values. It does not use repeat groups in v1. Repeated sets are expanded, preserving unequal weights/reps; combined unilateral sets remain single steps. Left set → side rest → right set → round rest applies only to explicit separate-side mode. The final round uses the exercise transition rest, without also adding an inter-set rest. This removes skipLastRestStep ambiguity and makes the preview match publication.

`renderers/planned_workout.py` renders that same semantic sequence. Bodyweight, load basis, aliases, side, time/lap termination and explicit omitted rests are visible. Any server step-limit rejection is surfaced with no truncation; repeat-group optimization can follow after device compatibility validation.

### 3. Additive commands and narrow modules

Proposed interface:

```text
training-sync garmin workout preview workout.json
training-sync garmin workout create workout.json --date 2026-09-13 --yes
training-sync garmin workout schedule WORKOUT_ID --date 2026-09-13 --yes
training-sync garmin workout show WORKOUT_ID
```

Create without --yes prints the local preview and performs no network writes. Date is optional for create (template only) and required for schedule. Date comes from the explicit argument, independently of source-note date. Preview is offline and needs neither Garmin login nor a vault root. CLI calls `use_cases/publish_workout.py`; provider DTOs stay in the adapter. Reuse `get_client`, known mappings and catalog infrastructure without importing vault code. Unknown/ambiguous exercises fail; explicit `garmin_name` may identify a catalog-backed substitute while preserving the original exercise name in descriptions and preview.

### 4. Semantic verification and recoverable publication

Read back name, sport, ordered executable steps, exercise identity, side description, reps/time/lap conditions, loads/units and every rest. Normalize provider-added IDs/default fields only; never ignore an expected behavior field. Schedule only after workout verification; check the exact workout ID and local calendar date afterward. Return IDs and Garmin URL with separate created/verified/scheduled states; never claim a watch has synced.

Use a local journal under the project's configuration directory, keyed by authenticated account plus plan key and canonical execution-content hash. Write journal state atomically before each mutation and store returned remote IDs immediately. Exclude provenance from the execution hash. Lock the key during publication to prevent concurrent duplicate writes. Reuse and reverify an existing successful publication. A changed creation payload under the same key is a conflict, not an implicit update. An explicitly requested update is a separate journaled operation with its own baseline, desired hash and revision.

On timeout with an unknown mutation outcome, retain an uncertain state and reconcile read-only before any retry. Include an opaque key/hash marker in the Garmin description to find a lost upload response; paginate bounded inventory as supported and adopt only one exact semantic match. Zero or multiple matches after bounded retries leave the operation unresolved with no blind repost. Scheduling checks ID/date for existing entries; a failure there retains the verified template for retry. No unrequested template deletion or completed-activity mutation.

## Risks / Trade-offs

- Library/provider behavior can differ from local assumptions → isolate DTOs, test normalized read-back, and require an opt-in real-device smoke test before claiming watch compatibility.
- Flat sequences can be longer → surface provider rejection and preserve the complete plan; never truncate.
- Exercise names or unilateral load conventions can be ambiguous → expose mappings/basis in preview and fail unresolved mappings.
- Local journal cannot provide universal cross-machine idempotency → remote marker reconciliation plus explicit unresolved states; document the local-account scope.
- Screenshots can omit rests or contain completed results → assistant must establish planning intent and fill explicit choices before calling the feature.

## Migration Plan

Add modules, commands, JSON examples and documentation. Existing import-strength/sync commands retain their interfaces. Run focused and full tests before updating the operational CLI installation. Rollback removes the new code only; published Garmin workouts remain remotely available. Live publication requires a separately requested smoke test and must not reuse today's already-executed workout.

## Multisport lifecycle extension

The following decisions extend the original create-only design and supersede its initial command subset.

### Portable endurance structure

Use sport values strength_training, cycling and running, with indoor/outdoor context separate from sport. Introduce ordered executable and repeat blocks in the planned domain. Each step separates role (warmup/work/recovery/cooldown), termination (seconds, meters or lap) and intensity target. Repeats expand deterministically into the same preview/verification sequence, preserving recovery after the last repetition when prescribed.

V1 target coverage includes watts for cycling AND running, pace for running, heart rate, and compatible cycling cadence targets. Units and bounds are explicit; intervals may have a single value or valid range. Zone/percentage inputs require a tested provider mapping or an explicit reference-based conversion shown in preview; never guess FTP, thresholds or heart-rate boundaries. Unsupported combinations, including unsupported simultaneous targets, fail visibly rather than being omitted. Reject nonfinite/nonpositive durations/distances and inverted target ranges. Unsupported indoor context must not silently become a claimed device capability.

Alternative: reuse the completed StrengthWorkout model. Rejected because prescription, targets and rests have a separate lifecycle. Provider limits must be tested; method/model presence alone does not prove device execution.

### Resource identity and mutation scope

Workout ID identifies a reusable template; schedule ID identifies one dated occurrence. Inventory includes both app-created and existing workouts with bounded pagination and explicit incomplete results. Names/dates are discovery aids, never sufficient destructive identity. Date is a local calendar date independent of source-note dates; time-of-day scheduling is not claimed.

Read full remote payloads before editing and preserve unrelated fields. Unsupported structures remain inspectable; reject edits that cannot preserve them instead of lossy recompilation. Provider-managed/read-only workouts fail with actionable permission errors. Known remote repeat structures may be retained if their semantics can be verified.

Preview semantic differences and the scope of any shared-template edit. Re-read the baseline immediately before mutation and reject drift; verify requested changes and preserved fields afterward. This is a best-effort optimistic check, not an atomic provider guarantee.

Date-specific edits default to a cloned variant replacing only the selected occurrence. Explicit template-wide edits retain the original workout ID and warn that other references may be affected. Removing a schedule entry never deletes the template. Template deletion requires exact ID and explicit authorization; reject deletion while references remain or impact cannot be established, requiring explicit unscheduling first.

Alternative: manage only app-created workouts. Rejected by the user. Alternative: overwrite the shared template for a one-date change. Rejected because it can change unrelated sessions.

### Recoverable calendar operations

For date-specific edits: fetch occurrence/baseline; create and verify variant; schedule and verify new occurrence on the selected date; recheck original; remove exactly the old schedule ID; verify its absence and preservation of other entries. Move follows the same add/verify/remove ordering without cloning the workout.

If any stage fails, expose original/replacement IDs and completed stages; do not report completion while both entries remain. Retain recoverable variants rather than deleting them automatically. Resume only the same authorized operation after reconciling remote state. A temporary duplicate is preferable to losing the original entry; no transaction atomicity is claimed.

Journal update/delete/move/replace operations as well as creation, with account-scoped resource locks and baseline/desired hashes. Reconcile uncertain deletion through true not-found responses, never authentication/network failures. Repeated schedule requests for the same workout/date are no-ops after verification unless duplicate intent is explicit. Other workouts on that date remain valid.

### Complete additive interface

Under training-sync garmin, extend workout preview/create/show/schedule with:
- workout list
- workout update WORKOUT_ID FILE_OR_STDIN --yes (explicit template scope)
- workout duplicate WORKOUT_ID --name NAME --yes
- workout delete WORKOUT_ID --yes
- calendar list --from DATE --to DATE
- calendar schedule WORKOUT_ID --date DATE --yes
- calendar move SCHEDULE_ID --date DATE --yes
- calendar remove SCHEDULE_ID --yes
- calendar replace SCHEDULE_ID FILE_OR_STDIN --yes (one-date variant)

The original workout schedule command may delegate to calendar schedule. Mutation commands without --yes only preview; authenticated reads may be needed for remote differences, while local plan preview remains offline. Return machine-readable IDs, links, verified/partial/uncertain states and nonzero failure exit codes with redacted errors.

Extend use_cases/publish_workout.py for creation/recovery and add use_cases/manage_planned_workouts.py for inventory and mutation orchestration. Keep provider DTO handling in garmin/planned_workouts.py and shared semantic rendering in renderers/planned_workout.py.

No push_workout_to_device calls belong in this version. Success means saved and scheduled as applicable, not downloaded or executed.

### Additional verification risks

Full-payload updates may discard external fields unless explicitly preserved; test that protection. Calendar replacement is non-atomic; test every failure boundary. Running power and indoor context require adapter fixtures and separately authorized compatible-device smoke tests. Automated tests must not publish or delete real workouts.
