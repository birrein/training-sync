## MODIFIED Requirements

### Requirement: Accept source-independent planned input
The system SHALL accept versioned JSON from a file or stdin without requiring a vault, source type, daily heading or source parser. It MUST validate explicit planning structure, numeric values, load basis and version before authentication or mutation. An optional `garmin_name` on a strength exercise SHALL be treated as an assistant-prepared, user-authorized provider substitute, validated against the Garmin catalog; it SHALL not be inferred from provenance or source text. Under schema version 1 each strength `sets` entry SHALL accept optional `repeat`, defaulting to 1, as a strictly positive integer count of consecutive whole sets. Mixed explicit and repeated entries MUST preserve order, termination, repetitions, load basis, side semantics and instructions. Expansion MUST precede canonical hashing; equivalent explicit and compact inputs MUST produce identical canonical content and execution hashes. The system MUST enforce a documented aggregate expansion bound before allocation, rejecting excessive input without truncation. Existing explicit inputs SHALL retain their canonical content; older readers require an upgrade to accept repeat. Exercise-level rests SHALL apply to the expanded physical sets.

#### Scenario: Equivalent sources
- **WHEN** an assistant prepares equivalent JSON from chat, a Fitbod screenshot or an arbitrarily formatted note
- **THEN** execution steps are identical regardless of optional provenance

#### Scenario: Invalid input
- **WHEN** input has an unknown field, unsupported version, nonfinite load, zero repetitions, unresolved duration range or conflicting termination fields
- **THEN** validation fails with a field-specific error before authentication

#### Scenario: Equivalent compact and explicit sets
- **WHEN** an entry with repeat N prescribes ten repetitions at 53 kg total and is compared with N identical explicit entries
- **THEN** both forms produce identical canonical content, execution hashes and physical sets without multiplying reps or load within a set

#### Scenario: Omitted repeat
- **WHEN** repeat is absent or equals 1
- **THEN** the entry produces one physical set with the same canonical representation as the previous explicit input

#### Scenario: Mixed entries and rests
- **WHEN** individual warm-up sets precede an entry repeated N times
- **THEN** their order is retained, inter-set rests occur between expanded physical sets, and the exercise transition occurs once after the last set

#### Scenario: Manual sets and explicit sides
- **WHEN** a time/LAP entry or a separate-side round has repeat N
- **THEN** N complete sets or rounds retain termination and side/rest semantics without invented repetitions or automatic Garmin grouping eligibility

#### Scenario: Invalid repeat
- **WHEN** repeat is zero, negative, fractional, boolean, a string or null
- **THEN** input fails with a field-specific error before authentication

#### Scenario: Excessive expansion
- **WHEN** total expanded input exceeds the documented safety bound
- **THEN** validation rejects it before allocation or mutation without truncating the workout

### Requirement: Preview the executable sequence
The system SHALL provide an offline preview of ordered physical sets, loads, side, warm-up and rest termination rules using the same expanded sequence submitted for publication. New strength prescriptions MUST explicitly define a timed or manual rest after every set including the final workout set. Missing/null required rests MUST fail preflight before authentication or mutation with an explanation requesting an explicit choice. No duration SHALL be invented. Historical omitted-rest payloads SHALL remain readable without automatic rewriting.

#### Scenario: Last RDL set transitions to hip thrust
- **WHEN** three RDL sets specify 165-second inter-set and transition rests
- **THEN** the preview and published sequence include one 165-second rest after the third set before hip thrust

#### Scenario: Combined unilateral sets by default
- **WHEN** two lateral-raise sets prescribe 15 repetitions per arm and 75-second round/transition rests
- **THEN** each set is one exercise step prescribing 15 per arm with instructions to complete both arms before the 75-second rest, including the final exercise transition, without doubling reps or loads

#### Scenario: Explicit separate-side rounds
- **WHEN** separate-side mode is explicitly requested for two Bulgarian rounds with 11 reps per side, 60-second side rests and 90-second round/transition rests
- **THEN** each round contains left 11, rest 60, right 11, rest 90, including the transition after the final round

#### Scenario: Manual Bilbo set
- **WHEN** a Bilbo set has manual-lap termination and a prescribed load
- **THEN** the plan preserves that load and manual termination without inventing a repetition target and retains its explicitly prescribed following rest

#### Scenario: Lap warm-up and final rest
- **WHEN** warm-up ends by lap and final exercise rest is explicitly timed or manual
- **THEN** warm-up requires manual advance and the sequence includes that final rest for post-set editing

#### Scenario: Missing terminal strength rest
- **WHEN** a new strength prescription has null or undefined final rest
- **THEN** preflight requests an explicit timed or manual rest instead of silently omitting or inventing it
