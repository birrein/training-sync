## Context

See proposal.md for motivation. `garmin/planned_workouts.py` generates a flat projection; `use_cases/publish_workout.py` compares top-level steps; `use_cases/manage_planned_workouts.py` rejects repeat groups and merges steps by position/count. The existing canonical plan already represents every physical set explicitly.

Live evidence from this task: Lower Body 2 uses RepeatGroupDTO with numberOfIterations, iterations end condition, childStepId, global stepOrder and skipLastRestStep. A targeted Upper 1 update was read back with five groups of two and unchanged expanded execution. This verifies Garmin storage, not device execution. Use sanitized fixtures, not account metadata from those responses.

User-reported device observation on 2026-09-14: skipping the final rest prevented editing the last set's weight and repetitions because that option appears during rest. This motivates retaining a rest after every strength set; it is a user observation, not a universal device compatibility test.

The prerequisite capability is now archived and in main specs. This change includes its modified input and preview requirements to cover optional `repeat` and the new final-rest policy. Historical read-back retains the ability to decode omitted rests.

## Goals / Non-Goals

**Goals:** deterministic compact DTOs, unchanged canonical hashes, one shared bounded decoder for verification and management, actionable errors for unsupported preservation cases.

**Non-Goals:** a new schema version, arbitrary circuits/nested repeats, endurance grouping, automatic remote migration, device push.

## Decisions

1. Extend the input parser in `domain/planned_workout.py` with optional `repeat` on each `sets` entry, default 1. Accept only positive integers, rejecting booleans, floats, strings, null and nonpositive values. Expand entries in order into the existing physical `PlannedSet` representation before canonical serialization/hashing. Preserve reps or time/LAP termination, load/basis and descriptions per copy. Mixed explicit and repeated entries are supported. `repeat` repeats whole sets, never reps or kilograms. Rest selection uses the expanded exercise: inter-set rest after every nonfinal physical set, transition rest once after the last. Explicit sides repeat a complete round. Manual sets can be repeated in input but remain ungrouped in Garmin. Bound aggregate expansion before allocating; document the safety limit and reject excess rather than truncate.

   Keep schema_version=1 as an additive extension for updated readers; older strict readers need an upgrade before receiving compact input. A compact entry and its equivalent explicit list must have identical canonical serialization and execution hash. Canonical output may be expanded; preserving compact spelling is not required. Keep `GarminWorkoutProjection.steps` expanded and group DTOs at the Garmin boundary based on eligibility, regardless of input spelling.

   Example: `"sets": [{"repeat": 3, "reps": 10, "load": {"kind": "mass", "kg": 53, "basis": "total"}}]`. Exercise-level rest fields still apply and must be explicit.
2. Group maximal eligible runs of repetition-based sets. Compare all meaningful fields including side/load basis and instructions. Do not discard differing free text merely to obtain grouping; the one-off script's removal of known series labels is not a general normalization rule. Keep manual Bilbo and explicit separate-side rounds flat in this version.
3. Every newly generated strength set, including singletons, Bilbo and the last workout set, must have an explicitly defined timed or manual rest. Missing/null rests fail preflight with a field-specific request for an explicit choice; do not invent a duration. Every generated group contains active plus rest and uses skipLastRestStep=false. Group only sets with equal following rests; retain a final set separately when its transition differs. Assign deterministic group/child references and global step order based on the observed Garmin shape.
4. Introduce a shared Garmin step-tree decoder with a bounded expansion, strict positive integer repeat validation, supported shape checks and skip-last-rest handling. Preserve unit and description comparison already used by `_compare_step`. Keep provider DTO-count limits separate from the expansion safety bound; do not infer device capacity from compression.
5. Verify both execution and requested layout for new writes. Existing flat publications can be verified semantically for journal recovery without a write. Canonical hashes remain unchanged; a layout conversion is an explicit update, not a new creation key or automatic migration.
6. Replace positional merge assumptions with supported-tree handling. Preserve template/segment metadata and semantically aligned step metadata. Strip/reassign structural IDs only where hierarchy changes require it. If distinct metadata cannot be merged losslessly into a repeated child, reject the conversion. Support updating and duplicating already-grouped templates and variant paths; do not merely remove the current repeat guard.

## Risks / Trade-offs

- Final-rest mistakes alter execution → compare the full expansion before write and after read-back, including manual and unequal transitions.
- Group-aware generation alone breaks update/recovery → exercise publication, journal retry, update, duplicate and variant paths with grouped fixtures.
- Per-set custom instructions/metadata prevent compacting → preserve them or reject unsafe updates instead of silently dropping them.
- Server persistence does not prove watch rendering → keep automated tests offline and make device smoke verification a separately reported optional step.

## Migration Plan

Implement in tested blocks: codec, generator/preview, verification, management. Historical flat/grouped workouts remain readable and verifiable, including skipLastRestStep=true. New strength writes require explicit rests after every set; legacy plans lacking them need an explicit prescription update. Do not silently add a rest during retry or duplication. Keep existing canonical hashes for unchanged content; an added rest changes the prescription and hash normally. No bulk rewrite. Rollback must keep grouped-read support for resources already written.
