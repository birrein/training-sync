# weightxreps-cardio-sync Specification

## Purpose
Define full-day Weight x Reps reconciliation that preserves representable bodyweight and strength state, encodes Garmin cardio with structured duration and distance fields, and verifies the saved day by read-back before success.

## Requirements
### Requirement: Preserve the complete mixed training day

The system MUST reconstruct the full Weight x Reps replacement with preserved strength activity and every cardio activity for the target date.

#### Scenario: Mixed strength and cardio day
- **WHEN** the target day contains existing strength blocks and Garmin supplies running and cycling activities
- **THEN** the replacement contains the strength blocks plus distinct structured rows for both cardio activities

### Requirement: Resolve every exercise before writes

The system MUST reject unresolved or ambiguous Weight x Reps exercise mappings before any local or remote write and MUST NOT silently create an exercise.

#### Scenario: Unknown cardio exercise
- **WHEN** a Garmin activity cannot be resolved to exactly one existing Weight x Reps exercise
- **THEN** preflight fails with the unresolved or ambiguous activity and neither destination is written

### Requirement: Resolve exercises using the complete catalog

When a Weight x Reps user identifier is configured, the system MUST retrieve the user's complete exercise catalog and use it during exercise resolution before performing any local or remote write.

#### Scenario: Configured user enables complete catalog lookup
- **WHEN** synchronization requires exercise resolution and a Weight x Reps user identifier is configured
- **THEN** the system retrieves the complete exercise catalog
- **AND** resolves required exercises against that catalog before writing either destination

#### Scenario: Complete catalog lookup fails
- **WHEN** the configured complete-catalog lookup cannot be completed
- **THEN** synchronization fails during preflight
- **AND** neither the daily note nor Weight x Reps is modified

### Requirement: Surface Weight x Reps GraphQL errors

The system MUST preserve actionable GraphQL error details returned by Weight x Reps, including when the response has a failed HTTP status, and MUST retain generic HTTP failure behavior when no GraphQL error payload is available.

#### Scenario: Failed HTTP response contains GraphQL errors
- **WHEN** Weight x Reps returns an HTTP 400 response with a GraphQL `errors` payload
- **THEN** synchronization fails with the GraphQL error details
- **AND** the generic HTTP status error does not hide those details

#### Scenario: Failed HTTP response lacks GraphQL errors
- **WHEN** Weight x Reps returns a failed HTTP response without a valid GraphQL `errors` payload
- **THEN** synchronization fails with the underlying HTTP status error

### Requirement: Encode cardio with distance

The system SHALL encode cardio with distance as a Weight x Reps set with `type: 2`, `t` containing actual duration in milliseconds, and save field `d: {val, unit}` containing the distance in centimeters multiplied by 100 and its supported unit string. Read-back SHALL compare the corresponding flat `d` and `dunit` values.

#### Scenario: Distance cycling activity
- **WHEN** Garmin provides a cycling activity lasting 3,620,000 milliseconds with a distance of 27.95 kilometers
- **THEN** its save set has `type: 2`, `t: 3620000`, and `d: {val: 279500000, unit: "km"}`, and read-back has `d: 279500000` and `dunit: "km"`

### Requirement: Encode duration-only cardio

The system SHALL encode cardio without distance as a Weight x Reps set with `type: 1` and `t` containing actual duration in milliseconds, without inventing `d` or `dunit`.

#### Scenario: Duration-only activity
- **WHEN** Garmin provides a cardio activity lasting 1,800,000 milliseconds and provides no distance
- **THEN** its set has `type: 1` and `t: 1800000` and has no fabricated distance fields

### Requirement: Retain unsupported Garmin metadata in comments

The system SHALL write the activity name and every provided heart rate, elevation, power, calories, and training-load value without a native Weight x Reps field into set comment `c`.

#### Scenario: Garmin provides all supported comment metadata
- **WHEN** an activity includes a name, average and maximum heart rate, elevation gain, average power, calories, and training load
- **THEN** `c` contains labeled values for each supplied metric and omits no supplied metric

#### Scenario: Garmin omits optional metadata
- **WHEN** an activity lacks power and training load
- **THEN** `c` contains the supplied metadata and does not invent power or training-load values

### Requirement: Confirm existing remote-day replacement

The system MUST require `--yes` before replacing a Weight x Reps day that already contains data.

#### Scenario: Existing remote day without confirmation
- **WHEN** the remote day contains data and `--yes` is absent
- **THEN** the command stops during preflight before either destination is written

#### Scenario: Existing remote day with confirmation
- **WHEN** the remote day contains data and `--yes` is present
- **THEN** the system submits the full-day replacement only after every preflight check passes

### Requirement: Verify structured remote fields by read-back

The system MUST read the saved day back and compare exercise identity and every expected set's `type`, `t`, `d`, and `dunit` before reporting success.

#### Scenario: Structured read-back matches
- **WHEN** the observed saved exercise and structured fields equal the expected full-day payload
- **THEN** verification succeeds and the command reports synchronization success

### Requirement: Report expected and observed verification details

The system MUST fail verification with expected-versus-observed details when an exercise or any `type`, `t`, `d`, or `dunit` value differs or is missing.

#### Scenario: Read-back mismatch
- **WHEN** a saved cycling set returns a different `type` or distance unit from the submitted set
- **THEN** the command fails and reports the expected and observed exercise and structured field values
