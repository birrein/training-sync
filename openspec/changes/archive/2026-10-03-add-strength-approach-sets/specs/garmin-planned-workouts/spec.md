## ADDED Requirements

### Requirement: Explicit exercise-specific approach sets
Under schema version 1 a strength set SHALL accept optional `role` with values `warmup` or `work`. Omitted role MUST default to `work` and preserve the previous canonical content and publication hash; explicit `work` SHALL normalize to the same identity. Explicit `warmup` MUST survive source repeat expansion, canonical serialization, preview and publication as a native Garmin Warm up step retaining its exercise identity, repetitions or manual/time termination, load and load basis. Roles MUST NOT be inferred from light weights, free text or exercise order. Unknown, empty, non-string or null roles MUST fail with a field-specific explanation before authentication or mutation. The existing generic workout warm-up SHALL remain supported independently.

#### Scenario: Requested bench approaches
- **WHEN** a plan explicitly marks bench approaches at 30 kg for 5 repetitions and 40 kg for 3 repetitions before three working sets at 53 kg for 12 repetitions
- **THEN** Garmin receives two ordered exercise-specific Warm up steps followed by the working prescription, with the defined rests and weights preserved

#### Scenario: Optional support does not add approaches
- **WHEN** an existing routine omits set roles and has no requested approach sets
- **THEN** its canonical representation, hash and executable prescription remain unchanged and no approach set is generated

#### Scenario: Equivalent repeated approaches
- **WHEN** one warmup entry repeated twice is compared with two explicit equivalent warmup entries
- **THEN** both have the same canonical content and hash, retaining the role for both sets

#### Scenario: Provider loses an approach role
- **WHEN** read-back changes a requested exercise-specific Warm up step to Exercise
- **THEN** verification fails and scheduling does not proceed

#### Scenario: Explicit working role preserves legacy identity
- **WHEN** an existing plan adds role work to all its ordinary sets without changing prescriptions
- **THEN** its canonical content, execution hash and Garmin prescription remain identical to the omitted-role form

#### Scenario: Invalid role fails before publication
- **WHEN** a strength set supplies null, a boolean, a number or an unsupported role such as recovery
- **THEN** validation fails with the exact exercises and sets field path before authentication or mutation

#### Scenario: Manual or timed approach
- **WHEN** an explicitly marked approach has manual-lap or time termination and a specified exercise and load
- **THEN** it retains native Warm up type, termination and load without invented repetitions

This requirement governs future planned prescriptions. It does not assert that completed Garmin activities retain the same role, classify completed sets, or automatically exclude them from vault, Weight x Reps or TrainerRoad working-set totals.
