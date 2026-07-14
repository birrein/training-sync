## ADDED Requirements

### Requirement: Fetch and stably order all activities

The system SHALL fetch every completed Garmin activity for the target date and SHALL order them by recorded start time with Garmin activity ID as a deterministic tie-breaker.

#### Scenario: Multiple activities on one date
- **WHEN** Garmin returns multiple completed activities for the target date in arbitrary response order
- **THEN** the system includes every activity exactly once in ascending start-time and activity-ID order

### Requirement: Reject an empty Garmin day before writes

The system MUST stop before any local or remote write when Garmin returns no completed activity for the target date.

#### Scenario: No activity exists
- **WHEN** Garmin returns zero completed activities for the target date
- **THEN** the command fails with a no-activity error and neither the daily nor Weight x Reps is written

### Requirement: Require an existing daily note

The system MUST resolve an already-existing daily note and training heading for the target date and MUST NOT create either one.

#### Scenario: Daily note is missing
- **WHEN** the target date has Garmin activities but its daily note does not exist
- **THEN** the command fails during preflight before any daily or Weight x Reps write

### Requirement: Render one combined training section

The system SHALL render all ordered Garmin activities into one replacement payload for the existing `## 🏃 Training` section.

#### Scenario: Combined multi-activity rendering
- **WHEN** the date contains strength, running, and cycling activities
- **THEN** the updated daily contains one training section whose activity blocks follow the stable Garmin order

### Requirement: Confirm non-empty daily replacement

The system MUST require `--yes` before replacing a non-empty daily training section.

#### Scenario: Existing training content without confirmation
- **WHEN** the daily training section contains non-whitespace content and `--yes` is absent
- **THEN** the command stops before any daily or Weight x Reps write and reports that confirmation is required

#### Scenario: Existing training content with confirmation
- **WHEN** the daily training section contains non-whitespace content and `--yes` is present
- **THEN** the system replaces that section only after all other preflight checks pass

### Requirement: Complete all preflight checks before writing

The system MUST validate Garmin activities, stable ordering keys, the daily path and section, credentials, exercise resolution, confirmation requirements, and the complete expected Weight x Reps payload before its first write.

#### Scenario: Late preflight input is invalid
- **WHEN** Garmin and daily validation succeed but an exercise mapping is unresolved
- **THEN** the command fails without changing either destination

### Requirement: Retain the daily on remote failure

The system SHALL update the daily before Weight x Reps and MUST retain the updated daily when the remote write or read-back verification fails.

#### Scenario: Weight x Reps fails after daily update
- **WHEN** all preflight checks pass, the daily replacement succeeds, and Weight x Reps then fails
- **THEN** the command reports a partial failure, preserves the updated daily, and returns a non-success result suitable for idempotent retry
