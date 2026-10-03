## Context

The planning domain previously supported a generic workout warm-up but no role on an individual strength set. Generic warm-up steps do not carry the same exercise, repetition and weight prescription as strength steps. The Garmin compiler already preserves exercise identity and load basis, and publication read-back already compares native step types before scheduling.

The user requests capability for future plans and decides when approaches are included. The workout currently being executed is outside this change. Implementation and focused tests were already present as local, uncommitted changes before this formal OpenSpec change was created. An isolated pre-change domain baseline subsequently failed the two new role tests; this establishes the missing capability but does not meet the historical test-first ordering. This process deviation is recorded rather than retroactively claiming that proposal or failing tests preceded code edits.

## Goals / Non-Goals

**Goals**
- Represent explicitly requested approaches at the strength-set level.
- Preserve legacy plans, canonical content and publication identity.
- Generate native Garmin Warm up steps with exercise, load and termination intact.
- Keep role boundaries through grouping, publication verification, update and duplication.
- Persist the user's preference that approaches are opt-in.

**Non-goals**
- Automatically prescribe approaches or infer them from weight, exercise order or notes.
- Modify the current Garmin workout or publish any real workout during development.
- Classify completed activities or automatically remove approaches from vault, Weight x Reps or TrainerRoad totals.
- Introduce per-set rest fields, alter other sports or migrate existing plans.

## Decisions

### 1. Add an optional role to each strength set

`PlannedSet.role` accepts `warmup` and `work` under schema version 1. The default is `work`; serialization omits that default so explicit work and omitted roles preserve legacy canonical hashes. Repeat expansion preserves the role. Invalid roles fail at the exact set field path before provider authentication or mutation.

A role on the set supports mixed prescriptions within one exercise. A separate exercise type or a global warm-up flag would not express that distinction as directly. Existing plans remain valid; consumers that have not adopted this additive field may reject plans that explicitly use it.

### 2. Use Garmin's native Warm up type with the strength prescription

The strength compiler emits native `warmup` for explicit approach sets and the existing `interval` type for work sets. It retains exercise identity, load basis and repetition, manual-lap or time termination. A short description also identifies the approximation. A description alone is insufficient because it cannot preserve a machine-readable role during verification.

The generic top-level workout warm-up remains a separate step. The change does not reinterpret its description as an exercise-specific prescription.

### 3. Respect role boundaries during grouping

The existing semantic grouping signature contains native step type, so otherwise identical approaches and work sets cannot share a group. Eligible same-role runs can still group. Manual-lap sets and explicit separate-side rounds remain ungrouped. Combined unilateral sets retain both sides within one series and their existing per-side repetition and load conventions.

Existing transition-rest handling is preserved, including `skipLastRestStep` and one explicit transition rest when the final rest differs from the inter-set rest.

### 4. Reuse the existing rest and read-back contracts

The model retains its current rest fields. Where approaches need a different inter-set rest from work, separate exercise entries can prescribe those rests; groups do not cross entries. No new rest schema is needed for this capability.

Publication verification already compares step type and prescription. A provider changing Warm up to Exercise must fail verification and prevent scheduling. Management operations parse and compile the same domain model, so update and duplication preserve the role without a second representation.

### 5. Separate planned intent from completed execution

Repository instructions and the hybrid-training-advisor skill require an explicit user request before adding approaches. A planned role is evidence of intent, not proof that completed Garmin activity data preserves that distinction. Completed synchronization and working-set accounting remain governed by their existing contracts and actual execution evidence.

## Risks / Trade-offs

- Garmin payload and read-back behavior are covered by offline provider-boundary tests. Watch execution has not been tested, and no real Garmin write is claimed.
- Adding a role intentionally changes the canonical identity when the set becomes a warmup. Legacy work-only plans keep their identity.
- Older readers may reject the new field; use the updated parser for plans containing explicit roles.
- Completed activity classification is outside scope. Consumers must not assume planned warmups are automatically excluded from completed working-set totals.
- The formal proposal and baseline failing tests followed the initial implementation in this instance. Future changes must follow the repository's test-first workflow.

## Migration Plan

1. Validate the formal OpenSpec change and retain it as an open change for the local implementation.
2. Use focused offline tests for domain identity, compilation, grouping, publication verification and management, and validate the updated skill.
3. Existing plans require no migration or re-publication. Use `role: "warmup"` only when the user requests approaches in a future plan.
4. If reverting support, explicitly review any plan using the new role before removing the field; silently treating its approach sets as work would lose intent. No live workout requires rollback for this change.

No commit or push is part of this request. A later authorized implementation commit can use `feat(garmin): support explicit strength approach sets`.
