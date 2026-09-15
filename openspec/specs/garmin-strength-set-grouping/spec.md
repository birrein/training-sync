# garmin-strength-set-grouping Specification

## Purpose
Present repeated strength sets compactly in Garmin Connect while preserving executable prescriptions and verified planned-workout management.

## Requirements

### Requirement: Automatically group equivalent consecutive strength sets
The system SHALL publish eligible runs of at least two consecutive sets within the same strength exercise as a repeat group. Eligibility MUST require equal exercise identity, repetition termination, load and load basis, side semantics, meaningful instructions and inter-set rests. It MUST preserve set order, keep manual-lap sets and explicit separate-side rounds ungrouped, and never combine distinct exercise entries. Running and cycling behavior SHALL remain unchanged.

#### Scenario: Equivalent sets with equal rests
- **WHEN** any eligible strength exercise has N consecutive equivalent sets, where N is an integer of at least two, with identical repetitions, load, load basis, side semantics, meaningful instructions and prescribed following rests
- **THEN** Garmin receives one N-iteration group preserving that exercise and its prescription, including the rest after every set and the final set, with skipLastRestStep=false

#### Scenario: Different prescriptions or instructions
- **WHEN** consecutive sets differ in weight, repetitions, termination, load basis or meaningful instructions
- **THEN** no group crosses that difference and all original prescriptions remain represented

#### Scenario: Bilbo and normal bench
- **WHEN** manual-lap Bilbo at 53 kg precedes two normal 12-repetition sets at 53 kg
- **THEN** Bilbo remains a manual step and only the normal sets are grouped

#### Scenario: Combined unilateral sets
- **WHEN** two sets prescribe 15 repetitions per arm at 5 kg with 75-second rests
- **THEN** the group retains the per-arm prescription and both-arms-before-rest instruction without multiplying repetitions or load

### Requirement: Preserve transition and terminal rests exactly
New strength writes MUST require an explicitly defined timed or manual rest after every set, including the final workout set, to retain the watch's post-set editing phase. Missing or null rests MUST fail preflight with a field-specific explanation before mutation; no duration SHALL be invented. Every generated group MUST use skipLastRestStep=false and expand to the prescribed sequence. If a transition differs, the system SHALL keep the affected sets separate rather than skip a group rest or double the transition. Manual rests MUST retain manual termination. Historical workouts with omitted rests SHALL remain readable without automatic rewriting.

#### Scenario: Final face pull editing phase
- **WHEN** two face pull sets specify 75 seconds after each set including the final workout set
- **THEN** the group keeps both rests with skipLastRestStep=false

#### Scenario: Missing final rest
- **WHEN** a new strength write requests no final rest or leaves it undefined
- **THEN** preflight requests an explicit timed or manual rest before any mutation

#### Scenario: Manual final rest
- **WHEN** the final set prescribes a manual rest
- **THEN** that rest remains available until manual advancement without an invented duration

#### Scenario: Different transition rest
- **WHEN** two identical sets have 75 seconds between sets and 120 seconds after the exercise
- **THEN** the two sets remain separate and execution contains active, rest 75, active, rest 120 exactly once each in that order

### Requirement: Preview and verify grouped execution
Offline preview SHALL disclose repeat counts and rest exceptions while retaining the full executable prescription. Remote verification MUST compare expanded semantics and verify the requested repeat representation on writes. Missing groups, wrong iteration counts, altered children or changed last-rest behavior MUST prevent a successful grouped-write result. Supported flat historical resources SHALL remain readable and semantically verifiable without forced migration.

#### Scenario: Provider changes iteration count
- **WHEN** a two-set group is saved as three iterations
- **THEN** read-back verification fails and scheduling does not proceed

#### Scenario: Provider flattens the requested representation
- **WHEN** Garmin returns equivalent flat execution after a requested grouped write
- **THEN** verification reports that grouped representation was not retained rather than claiming grouped-write success

#### Scenario: Existing publication retry
- **WHEN** unchanged canonical content resolves to a verified historical flat publication
- **THEN** retry reuses its identity without creating a duplicate or implicitly rewriting its representation

### Requirement: Safely manage supported grouped templates
Authorized updates, duplication and date-specific variants SHALL support ordinary strength repeat groups with fixed positive iteration counts and supported children. They MUST preserve unrelated metadata, stale-baseline checks and exact template/calendar scope. A representation-only update MUST preserve expanded execution. Unsupported structures or metadata conflicts that cannot be preserved through regrouping MUST fail before mutation. Grouping SHALL NOT modify completed activities, vault records or Weight x Reps records.

#### Scenario: Convert an existing flat template
- **WHEN** an authorized update groups equivalent sets on an exact flat workout
- **THEN** its workout ID and unrelated fields are preserved, and execution and grouping are verified after saving

#### Scenario: Edit an existing grouped template
- **WHEN** an authorized supported load change targets a grouped workout
- **THEN** the updated prescription and preserved content are verified without dropping groups or unrelated metadata

#### Scenario: Unsupported repeat structure
- **WHEN** a template contains nested or conditional repeats outside supported strength groups
- **THEN** inspection remains available and unsafe mutation is rejected before writing

#### Scenario: Conflicting per-set metadata
- **WHEN** two otherwise equal sets carry distinct provider metadata that one grouped child cannot preserve
- **THEN** an update requiring that merge is rejected with a specific explanation before writing
