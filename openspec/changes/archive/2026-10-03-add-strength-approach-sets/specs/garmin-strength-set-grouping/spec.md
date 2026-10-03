## MODIFIED Requirements

### Requirement: Automatically group equivalent consecutive strength sets
The system SHALL publish eligible runs of at least two consecutive sets within the same strength exercise as a repeat group. Eligibility MUST require equal exercise identity, explicit set role, repetition termination, load and load basis, side semantics, meaningful instructions and inter-set rests. It MUST preserve set order, keep manual-lap sets and explicit separate-side rounds ungrouped, and never combine distinct exercise entries. Running and cycling behavior SHALL remain unchanged.

#### Scenario: Equivalent sets with equal rests
- **WHEN** any eligible strength exercise has N consecutive equivalent sets, where N is an integer of at least two, with identical repetitions, load, load basis, side semantics, meaningful instructions and prescribed following rests
- **THEN** Garmin receives one N-iteration group preserving that exercise and its prescription, including the rest after every set and the final set, with skipLastRestStep=false

#### Scenario: Different prescriptions or instructions
- **WHEN** consecutive sets differ in weight, repetitions, termination, load basis or meaningful instructions
- **THEN** no group crosses that difference and all original prescriptions remain represented

#### Scenario: Equal prescriptions with different roles
- **WHEN** consecutive sets have identical exercise, repetitions and load but some explicitly have role warmup and others have role work
- **THEN** no group crosses the role boundary; eligible runs within each role retain native Warm up or Exercise children, respectively

#### Scenario: Bilbo and normal bench
- **WHEN** manual-lap Bilbo at 53 kg precedes two normal 12-repetition sets at 53 kg
- **THEN** Bilbo remains a manual step and only the normal sets are grouped

#### Scenario: Combined unilateral sets
- **WHEN** two sets prescribe 15 repetitions per arm at 5 kg with 75-second rests
- **THEN** the group has two iterations, each retaining the per-arm prescription and both-arms-before-rest instruction; this is two series per muscle, not four, without multiplying repetitions or load
