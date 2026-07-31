## ADDED Requirements

### Requirement: Represent completed activities independently of providers
The system SHALL represent a completed activity with provider-neutral identity, local start time, activity type, duration, supported objective summaries, optional strength content, provenance, and references to source artifacts without exposing a provider payload as the canonical interface.

#### Scenario: Garmin activity becomes canonical
- **WHEN** a completed Garmin activity has been decoded and its objective fields validated
- **THEN** the canonical activity contains normalized values and Garmin provenance while Garmin-only payload fields remain behind the Garmin adapter

#### Scenario: Dense telemetry remains a source artifact
- **WHEN** an original FIT file contains heart-rate, GPS, or other dense streams
- **THEN** the canonical activity references the original artifact without requiring every sample to be copied into the canonical model

### Requirement: Distinguish imported strength evidence from completed activity
The system MUST represent screenshot-derived or file-derived strength evidence as a strength import until the corresponding Garmin activity has been updated and read back successfully.

#### Scenario: Fitbod screenshots are imported
- **WHEN** exercises, sets, repetitions, and loads are extracted from Fitbod screenshots
- **THEN** the system creates a strength import and does not yet claim that a completed canonical activity exists

#### Scenario: Garmin verification promotes the import
- **WHEN** the strength import is applied to Garmin and Garmin read-back matches the expected title, exercise order, active sets, repetitions, and loads
- **THEN** the verified Garmin result can become the canonical completed activity

#### Scenario: Garmin verification fails
- **WHEN** Garmin read-back does not match the expected strength import
- **THEN** the system retains the import as unverified evidence and MUST NOT synchronize it downstream as a completed activity

### Requirement: Represent strength structure and load without provider leakage
The system SHALL preserve ordered exercises and sets, set role, repetitions, and structured load forms including mass, bodyweight, assistance, resistance, and non-load primer work.

#### Scenario: Mixed strength session is normalized
- **WHEN** a session contains weighted rows, bodyweight dips, band-assisted chin-ups, warm-ups, and primer sets
- **THEN** the canonical strength session preserves their order and distinct load and set roles without inventing kilograms for non-mass work

### Requirement: Preserve effort at its observed scope
The system MUST represent RIR or RPE at set, exercise, or session scope with provenance and MUST NOT silently expand an observation to a more granular scope.

#### Scenario: Exercise-level RIR is supplied
- **WHEN** the user reports `chin-up RIR 1` for the exercise but not for each set
- **THEN** the canonical model stores one exercise-scoped RIR observation and does not assert that every set had RIR 1

#### Scenario: Weight x Reps requires set RPE
- **WHEN** a Weight x Reps projection derives RPE 9 from an RIR 1 observation
- **THEN** the projected value records its derivation and the original RIR observation remains unchanged

#### Scenario: Global RPE is supplied
- **WHEN** the user reports a global session RPE
- **THEN** the system stores it separately from exercise or set effort and separately from Feel or recovery

### Requirement: Resolve authority by field and retain provenance
The system MUST prefer an explicit current user correction, use verified Garmin execution for completed objective data, use vault evidence for subjective context, and MUST surface unresolved material conflicts instead of silently choosing a destination replica.

#### Scenario: Vault and Garmin provide different RIR information
- **WHEN** Garmin has no exercise RIR and the vault contains a current user-reported exercise RIR
- **THEN** the subjective observation comes from the vault while objective execution remains sourced from Garmin

#### Scenario: Destination differs from corrected Garmin
- **WHEN** a destination replica contains objective sets or duration that differ from the verified Garmin activity
- **THEN** the canonical activity retains Garmin objective data and the difference is exposed as replica drift

### Requirement: Use stable provider-neutral exercise identity
The system SHALL identify exercises with a stable local key, preferred name, aliases, and optional provider bindings, and MUST reject normalized keys, names, or aliases that ambiguously identify different exercises.

#### Scenario: One exercise has multiple provider identities
- **WHEN** `Chin Up` has Garmin, vault, and Weight x Reps names or IDs
- **THEN** all bindings resolve to one stable local exercise key

#### Scenario: Duplicate normalized alias is configured
- **WHEN** the same normalized alias points to two different local exercise keys
- **THEN** catalog validation fails before any local or remote training mutation

### Requirement: Migrate existing Weight x Reps mappings safely
The system MUST read the existing Weight x Reps-centered mapping format during migration and MUST create a backup and validate the neutral representation before writing a converted mapping.

#### Scenario: Existing mapping is used without mutation
- **WHEN** an existing mapping file is loaded only to resolve an exercise
- **THEN** the system can use it without forcing an immediate rewrite

#### Scenario: Mapping mutation triggers conversion
- **WHEN** a mapping operation needs to persist the neutral catalog format
- **THEN** the previous file is backed up, the converted catalog is validated, and the saved file is read back before success

### Requirement: Keep canonical activity separate from remote replicas
The system SHALL model each provider copy as an activity replica with provider identity, remote ID, external ID when available, source type, and observed state without treating replica deletion as deletion of the canonical activity.

#### Scenario: Intervals duplicate is deleted
- **WHEN** one Intervals.icu replica is deleted while the canonical Garmin activity is retained
- **THEN** only that replica changes lifecycle state and the canonical activity remains completed
