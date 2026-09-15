## Context

See proposal.md for motivation. `garmin/planned_workouts.py` generates a flat projection; `use_cases/publish_workout.py` compares top-level steps; `use_cases/manage_planned_workouts.py` rejects repeat groups and merges steps by position/count. The existing canonical plan already represents every physical set explicitly.

Live evidence from this task: Lower Body 2 uses RepeatGroupDTO with numberOfIterations, iterations end condition, childStepId, global stepOrder and skipLastRestStep. A targeted Upper 1 update was read back with five groups of two and unchanged expanded execution. This verifies Garmin storage, not device execution. Use sanitized fixtures, not account metadata from those responses.

The prerequisite capability is in completed but unarchived `add-garmin-planned-workouts`; keep it intact and sync/archive it before archiving this additive capability. Git status currently fails because the Xcode license is not accepted; planning creates only a new change directory. Recheck working-tree status before implementation, using an available working Git installation if necessary.

## Goals / Non-Goals

**Goals:** deterministic compact DTOs, unchanged canonical hashes, one shared bounded decoder for verification and management, actionable errors for unsupported preservation cases.

**Non-Goals:** new input schema, arbitrary circuits/nested repeats, endurance grouping, automatic remote migration, device push.

## Decisions

1. Keep `GarminWorkoutProjection.steps` expanded and use grouped DTOs in its payload. Add a representation summary to offline preview. Group at the Garmin adapter boundary, using exercise boundaries and canonical set semantics; changing the domain to repeats would unnecessarily alter inputs and idempotency.
2. Group maximal eligible runs of repetition-based sets. Compare all meaningful fields including side/load basis and instructions. Do not discard differing free text merely to obtain grouping; the one-off script's removal of known series labels is not a general normalization rule. Keep manual Bilbo and explicit separate-side rounds flat in this version.
3. A group contains active and inter-set rest when present. Equal terminal rest stays inside the loop. An absent or different terminal rest uses skipLastRestStep=true, with a different transition appended once outside. With no rests, repeat only the active child. Assign deterministic group/child references and global step order based on the observed Garmin shape.
4. Introduce a shared Garmin step-tree decoder with a bounded expansion, strict positive integer repeat validation, supported shape checks and skip-last-rest handling. Preserve unit and description comparison already used by `_compare_step`. Keep provider DTO-count limits separate from the expansion safety bound; do not infer device capacity from compression.
5. Verify both execution and requested layout for new writes. Existing flat publications can be verified semantically for journal recovery without a write. Canonical hashes remain unchanged; a layout conversion is an explicit update, not a new creation key or automatic migration.
6. Replace positional merge assumptions with supported-tree handling. Preserve template/segment metadata and semantically aligned step metadata. Strip/reassign structural IDs only where hierarchy changes require it. If distinct metadata cannot be merged losslessly into a repeated child, reject the conversion. Support updating and duplicating already-grouped templates and variant paths; do not merely remove the current repeat guard.

## Risks / Trade-offs

- Final-rest mistakes alter execution → compare the full expansion before write and after read-back, including manual and unequal transitions.
- Group-aware generation alone breaks update/recovery → exercise publication, journal retry, update, duplicate and variant paths with grouped fixtures.
- Per-set custom instructions/metadata prevent compacting → preserve them or reject unsafe updates instead of silently dropping them.
- Server persistence does not prove watch rendering → keep automated tests offline and make device smoke verification a separately reported optional step.

## Migration Plan

Implement in tested blocks: codec, generator/preview, verification, management. Existing canonical JSON and flat workouts remain valid. Newly requested writes use compact representation; no bulk rewrite. Preserve existing journal identity and require explicit updates for representation changes. Rollback must keep grouped-read support for resources already written; reverting only new grouping emission is safe, reverting all decoder support is not.
