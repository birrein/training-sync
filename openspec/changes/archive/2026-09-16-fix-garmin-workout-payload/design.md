## Context

See proposal.md for motivation. Current projection in `src/training_sync/garmin/planned_workouts.py` emits mass in grams with a string weightUnit, textual preferredEndConditionUnit values and internal metadata. `publish_workout.py` compares units by string conversion and falls back to gram interpretation; structured Garmin units therefore need explicit normalization. Its upload exception handler retains the exception class but loses provider details. Management paths share portions of verification and have their own write helpers.

Observed evidence from 2026-09-16:
- Original request reproduced HTTP 500 / MismatchedInputException after a complete 485-template inventory found no match.
- Corrected request converted weightValue 50000 / weightUnit "gram" to 50 / {unitId: 8, unitKey: "kilogram", factor: 1000.0}; set preferredEndConditionUnit to null; removed originalExerciseName, garminName, repetitionCount, weightBasis and loadKind; and matched sport displayOrder 4 from a saved workout.
- All 27 returned steps were checked for exercise, comment, termination, load and rest, and the exact 2026-09-16 calendar occurrence was verified. Dragon Flag already mapped correctly to CRUNCH / REVERSE_CRUNCH_ON_A_BENCH.
- Multiple fields changed together. Success validates the combined representation, not each field's individual causal role. Sanitized fixtures must record this limitation; temporary scripts are supporting evidence, not durable dependencies.

The current checkout still has dirty `group-garmin-strength-sets` planning artifacts; its main grouping spec is not yet present here. Implement against the selected checkout, composing with that change if merged, without overwriting its artifacts. This proposal adds requirements rather than replacing overlapping preview/rest requirements.

## Goals / Non-Goals

**Goals:** A consistent Garmin transport boundary and read-back normalization across planned-workout write paths; durable regression fixtures and safe diagnostics/recovery.

**Non-Goals:** Public schema changes, altered prescriptions, a new Dragon Flag mapping, new repeat shapes, automatic workout migration, journal resets, device testing or completed-activity synchronization changes.

## Decisions

1. Keep domain/canonical identity independent of wire encoding. Build a provider-safe payload from validated projection using explicit compatible fields; retain semantic metadata locally and meaningful instructions in descriptions. Use kilogram objects for mass and null preferred units for the reproduced strength reps/time/lap cases. Validate endurance-specific representations separately rather than blindly nulling all units. Apply transformation recursively only to supported groups. Avoid ad hoc conversion at one CLI call site because updates and variants must share the contract. Preserve unrelated supported remote metadata when managing existing templates; an allowlist for generated fields must not strip arbitrary existing content silently.

2. Normalize saved units explicitly for verification. Recognize known unit keys/IDs and consistent factors; reject inconsistent or unknown units. Compare canonical mass and termination independently of serialization. Accept legacy gram data where supported; do not accept absent units as grams by default. Missing repetitionCount is not a mismatch if authoritative repetition termination carries the target. Compare original/substitute and side/load instructions through the preserved descriptions, retaining grouping verification when available.

3. Use sanitized, minimal accepted/rejected/read-back fixtures under `tests/fixtures/garmin/` with no owner identifiers or private source prose. A boundary fake must reject incompatible types and return provider-shaped normalized JSON, rather than echoing the application's payload. Fixtures cover weighted, bodyweight, explicit substitutes, manual steps and supported repeat children. No extra live uploads solely to isolate a field's causality.

4. Extract only allowlisted diagnostic fields (stage, HTTP status, provider error code/type and reference ID), with bounded text and safe fallback. Preserve these separately from reconciliation errors through result, CLI and journal. Do not stringify arbitrary HTTP responses. Keep uncertain classification for ambiguous writes; informative errors do not justify clearing a journal or creating a new plan key.

5. Keep existing canonical markers/hashes stable. Transport hash changes must not invalidate semantic identity. Recovery must recognize the manually corrected remote template by marker plus normalized execution and adopt it without rewriting it. Use fixtures for this path; any live check is read-only unless a separate new write is explicitly requested.

## Risks / Trade-offs

- Garmin's undocumented wire schema can vary → Base compatibility on accepted fixture shapes, reject unknown units and clearly label offline versus live verification.
- Grouping work may land during implementation → Inspect its actual baseline and run equivalent flat/grouped contracts; do not weaken final-rest or representation verification.
- Fake round trips can hide wire incompatibility → Enforce independent request validation and provider-shaped responses.
- Richer errors can leak secrets → Allowlist fields and include adversarial redaction tests for output and persistence.
- Existing uncertain journals may not have historical provider details → Preserve what exists; do not fabricate lost diagnostics or automatically retry uploads.

## Migration Plan

Implement test-first in focused blocks. Preserve source JSON, canonical keys and journal entries; no bulk remote migration. Re-run read-only verification of the already-created workout if available. Rollback code without deleting journals or remote templates; an older verifier may then report an unresolved state rather than safely adopting a corrected payload.
