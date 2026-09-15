## Purpose

Manage verified Garmin strength, cycling/indoor cycling and running workouts and their independent calendar entries from a portable plan independent of chat, screenshot, note or other source formats.

## ADDED Requirements

### Requirement: Accept source-independent planned input
The system SHALL accept versioned JSON from a file or stdin without requiring a vault, source type, daily heading or source parser. It MUST validate explicit planning structure, numeric values, load basis and version before authentication or mutation. An optional `garmin_name` on a strength exercise SHALL be treated as an assistant-prepared, user-authorized provider substitute, validated against the Garmin catalog; it SHALL not be inferred from provenance or source text.

#### Scenario: Equivalent sources
- **WHEN** an assistant prepares equivalent JSON from chat, a Fitbod screenshot or an arbitrarily formatted note
- **THEN** execution steps are identical regardless of optional provenance

#### Scenario: Invalid input
- **WHEN** input has an unknown field, unsupported version, nonfinite load, zero repetitions, unresolved duration range or conflicting termination fields
- **THEN** validation fails with a field-specific error before authentication

### Requirement: Preview the executable sequence
The system SHALL provide an offline preview of ordered sets, loads, side, warm-up and rest termination rules using the same sequence submitted for publication.

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
- **THEN** the plan preserves that load and manual termination without inventing a repetition target

#### Scenario: Lap warm-up and final rest
- **WHEN** warm-up ends by lap and final exercise rest is explicitly null
- **THEN** warm-up requires manual advance and the sequence ends after the final active step

### Requirement: Preserve exercise identity and load semantics
The system MUST reject unresolved or ambiguous Garmin exercise mappings and MUST show original and substitute names when an explicit substitute is supplied. It SHALL distinguish bodyweight, total mass and per-hand mass without silently multiplying values.

#### Scenario: Explicit substitute
- **WHEN** Dragon Flag explicitly names Reverse Crunch on a Bench as its Garmin substitute
- **THEN** preview exposes both names and the original name remains in the published description

#### Scenario: Unmapped exercise
- **WHEN** an exercise has no resolvable provider identity
- **THEN** publication stops rather than sending UNKNOWN

### Requirement: Verify creation and scheduling independently
The system SHALL require explicit apply authorization, verify saved executable semantics before scheduling, and verify the exact workout ID and explicit local date before claiming scheduled success. Template creation without a date SHALL be supported.

#### Scenario: Date independent of source
- **WHEN** a plan originates in a September 12 note and publication requests September 13
- **THEN** the verified calendar entry is September 13

#### Scenario: Saved rest mismatch
- **WHEN** Garmin accepts a payload but read-back omits an expected rest
- **THEN** the operation reports verification failure and does not schedule it

#### Scenario: Calendar failure
- **WHEN** template verification succeeds but scheduling fails
- **THEN** the result retains the template ID and reports scheduling failure separately

### Requirement: Recover without blind duplication
The system SHALL reuse verified publications for the same account, plan key and content, reject changed creation content under an existing key unless submitted as a distinct explicit update operation, and serialize concurrent publications of that key. It MUST reconcile uncertain write outcomes before attempting another write.

#### Scenario: Retry after calendar failure
- **WHEN** the same verified plan is retried after a calendar failure
- **THEN** the existing template is reverified and scheduling resumed without creating another template

#### Scenario: Lost upload response
- **WHEN** an upload times out after Garmin may have accepted it
- **THEN** read-only reconciliation adopts one exact matching publication or reports unresolved state without blindly uploading again

### Requirement: Keep planned and completed lifecycles distinct
The system MUST preserve all completed activities and MUST NOT mark a published workout completed, modify vault/Weight x Reps records, delete templates without explicit authorization or claim device delivery as a result of creation or scheduling.

#### Scenario: Successful planned publication
- **WHEN** a workout has been created and scheduled successfully
- **THEN** the result includes verified Garmin workout/calendar IDs and a link while completed activity records remain unchanged


### Requirement: Represent multideporte interval prescriptions
The system SHALL support strength, cycling including indoor context, and running plans. It MUST separate step termination from intensity, preserve warm-up, work, recovery, cooldown and repeated block order, and support time/distance/manual interval termination where applicable. It SHALL support explicit power targets for cycling and running, running pace, heart rate and compatible cycling cadence targets. Unsupported provider mappings or target combinations MUST fail visibly before mutation rather than silently changing the prescription.

#### Scenario: Running power intervals
- **WHEN** a running workout prescribes five repetitions of three minutes at 250-270 watts and two minutes of recovery
- **THEN** preview and saved semantics preserve all five work/recovery pairs, time termination, watt units and target bounds

#### Scenario: Distance-based running
- **WHEN** a running workout prescribes six 400-meter intervals with an explicit pace range and 90-second recoveries
- **THEN** the system preserves distance termination independently of pace and time-based recovery

#### Scenario: Indoor cycling sequence
- **WHEN** an indoor cycling plan specifies a warm-up, repeated power intervals with recovery and a cooldown
- **THEN** preview and publication preserve the complete sequence and disclose the provider representation of indoor context

#### Scenario: Unsupported or unresolved target
- **WHEN** a target requires an unavailable threshold reference or lacks a supported provider mapping
- **THEN** publication stops with a field-specific explanation without inventing a threshold or dropping the target

### Requirement: Inventory existing and application-created resources
The system SHALL list and read workouts regardless of their creator subject to Garmin permissions, and SHALL list calendar entries within a requested bounded date range. Results MUST distinguish workout IDs from schedule IDs, expose pagination/incomplete results, and report exact not-found, unsupported or access-denied states.

#### Scenario: Manually created workout
- **WHEN** an accessible workout was created manually in Garmin
- **THEN** it can be listed and inspected without an application creation marker

#### Scenario: Multiple entries on one date
- **WHEN** two calendar entries share a date or title
- **THEN** each retains its exact schedule and workout identity and mutation is blocked until the target is unambiguous

### Requirement: Update and duplicate workouts safely
The system SHALL support explicitly authorized template updates and duplication for supported new or existing workouts. It MUST preview differences, preserve unrelated content, reject stale baselines or unsafe unsupported structures, and verify saved semantics. Template-wide edits MUST be identified as affecting the shared template, not one occurrence.

#### Scenario: Existing workout load edit
- **WHEN** an exact existing workout is selected for an authorized template-wide load change
- **THEN** its workout ID and unrelated fields are preserved and the changed load is read back before success

#### Scenario: Concurrent remote edit
- **WHEN** the remote baseline changed after preview
- **THEN** the system rejects the stale mutation and requests a refreshed preview rather than overwriting it

#### Scenario: Unsupported structure
- **WHEN** an existing workout contains content that cannot be preserved by an edit
- **THEN** inspection remains available but the unsafe edit is rejected without dropping content

#### Scenario: Duplicate template
- **WHEN** duplication of an exact accessible workout is authorized
- **THEN** a new workout is created and verified without modifying the original or copying calendar entries implicitly

### Requirement: Manage calendar occurrences independently
The system SHALL schedule, move and remove exact calendar occurrences separately from template CRUD. It MUST verify the exact workout ID, schedule ID and local date, preserve unrelated entries and leave templates unchanged when moving or removing an occurrence.

#### Scenario: Move to another date
- **WHEN** one schedule ID is authorized to move from Monday to Tuesday
- **THEN** the same workout is verified on Tuesday, the original occurrence is verified absent, and other occurrences remain unchanged

#### Scenario: Remove only the occurrence
- **WHEN** removal of one schedule ID is authorized
- **THEN** that occurrence is absent after verification while the reusable workout remains available

#### Scenario: Repeated schedule request
- **WHEN** scheduling the same workout/date is retried without explicit duplicate intent
- **THEN** the existing matching occurrence is verified and reused instead of creating another

### Requirement: Isolate single-date prescription changes
The system SHALL default changes scoped to a specific date to a workout variant replacing only the selected occurrence. It MUST preserve the original template and other dates, verify the replacement before removing the original occurrence, and expose partial failure without silently deleting recovery resources.

#### Scenario: Change tomorrow only
- **WHEN** a shared Upper workout is scheduled on multiple dates and only tomorrow's bench load is changed
- **THEN** a verified variant replaces only tomorrow's exact occurrence while the original workout and other dates retain their previous prescription

#### Scenario: Replacement scheduled but original removal fails
- **WHEN** the replacement is verified but removal of the original occurrence fails
- **THEN** the result reports partial state with both IDs, does not claim completion, and a retry reconciles those entries without creating another variant

### Requirement: Delete only exact authorized templates
The system SHALL support explicitly authorized deletion of exact workout IDs with an impact preview and verified absence. It MUST reject deletion while calendar references remain or impact cannot be determined, require explicit unscheduling first, and never delete completed activities.

#### Scenario: Unscheduled template deletion
- **WHEN** deletion of an exact unreferenced workout is authorized
- **THEN** only that workout is deleted and its absence is verified

#### Scenario: Referenced template deletion
- **WHEN** a template still has scheduled occurrences or reference discovery is incomplete
- **THEN** no deletion occurs and the system explains the references or unresolved impact

### Requirement: Verify all mutations and recover partial outcomes
The system MUST require explicit apply authorization for every mutation, provide preview-only behavior without it, verify changed and preserved semantics, and reconcile uncertain outcomes before retry. It SHALL expose separate operation stages, resource IDs, actionable redacted errors and non-success states for partial or unverified results.

#### Scenario: Lost deletion response
- **WHEN** deletion times out
- **THEN** the system checks the exact resource read-only and distinguishes verified absence from authentication or network failure before any retry

#### Scenario: Target mismatch after update
- **WHEN** an accepted update reads back a different running power range
- **THEN** the operation reports verification failure rather than successful publication

### Requirement: Rely on normal calendar synchronization
The system SHALL leave device download to normal Garmin Connect synchronization in this version and MUST NOT perform explicit device push or equate calendar verification with device receipt.

#### Scenario: Workout scheduled successfully
- **WHEN** the workout and occurrence have been verified in Garmin Connect
- **THEN** the result reports saved/scheduled status and normal synchronization guidance without claiming watch or Edge receipt
