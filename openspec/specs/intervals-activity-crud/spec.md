# Purpose

Define safe, secret-redacted Intervals.icu activity inventory and lifecycle operations for canonical activity replicas.

## Requirements

### Requirement: Authenticate without exposing Intervals credentials
The system MUST load the Intervals.icu personal API key from local secret configuration, use the documented personal-account authentication form, and MUST redact the key from previews, errors, logs, and saved artifacts.

#### Scenario: Intervals request is previewed
- **WHEN** a caller previews an Intervals.icu read or mutation
- **THEN** the output identifies the provider and operation without printing the API key or authorization header

### Requirement: Inventory and read completed activities
The system SHALL list Intervals.icu completed activity summaries for a bounded requested date range and SHALL read a specific activity by exact remote ID.

#### Scenario: Date inventory is requested
- **WHEN** the caller requests Intervals.icu activities for one local date
- **THEN** the adapter returns normalized replica identity, local start, activity type, title, source type, external ID, and supported comparison fields for that date

#### Scenario: Exact activity is requested
- **WHEN** the caller supplies an Intervals.icu activity ID
- **THEN** the adapter returns that activity or an explicit not-found result

### Requirement: Match replicas deterministically
The system MUST prefer exact remote or external identity and MAY use normalized local start, compatible activity type, and objective duration or distance only when the fallback produces exactly one candidate.

#### Scenario: Garmin external ID matches
- **WHEN** an Intervals.icu activity has an `external_id` equal to the canonical Garmin activity ID
- **THEN** the system matches it as that activity's replica

#### Scenario: Fallback produces one candidate
- **WHEN** no external ID matches and exactly one activity has a compatible local start, type, and objective duration or distance
- **THEN** the plan may use the fallback match and MUST show the match evidence

#### Scenario: Multiple candidates remain
- **WHEN** more than one Intervals.icu activity satisfies fallback matching
- **THEN** the system reports ambiguity and MUST NOT automatically update or delete any candidate

### Requirement: Upload a completed activity with stable external identity
The system SHALL create an Intervals.icu replica by uploading a supported canonical source artifact and SHALL send the canonical Garmin activity ID as `external_id` when available.

#### Scenario: Missing Garmin replica is uploaded
- **WHEN** a canonical Garmin activity has no matching Intervals.icu replica and its original FIT, TCX, GPX, ZIP, or GZ artifact is available
- **THEN** the system uploads the artifact with stable external identity after authorization

#### Scenario: Upload is verified
- **WHEN** Intervals.icu accepts an upload
- **THEN** the system re-reads the returned or discovered remote activity and verifies its remote ID, external ID, local start, activity type, and supported objective fields

#### Scenario: Matching replica already exists
- **WHEN** one verified Intervals.icu replica already matches the canonical activity
- **THEN** create reconciliation produces a no-op and does not upload a duplicate

### Requirement: Update supported activity fields only
The system SHALL update only explicitly changed fields supported by the published Intervals.icu activity update contract and MUST reject updates for remote source types that Intervals.icu marks as non-updatable.

#### Scenario: Uploaded activity title is corrected
- **WHEN** an application-uploaded Intervals.icu activity requires only a supported title correction
- **THEN** the plan includes only that changed field and verifies the corrected title by read-back

#### Scenario: Strava-sourced activity update is requested
- **WHEN** the selected Intervals.icu activity has source type `STRAVA`
- **THEN** planning rejects the update before mutation and explains that the published contract does not permit it

### Requirement: Delete only an exact authorized activity
The system MUST require an exact Intervals.icu remote ID and explicit authorization before deleting an activity and MUST NOT infer deletion from an ambiguous fallback match.

#### Scenario: Exact duplicate is deleted
- **WHEN** the caller authorizes deletion of an exact duplicate remote ID after preview identifies the replica to retain
- **THEN** the adapter deletes only that remote activity and verifies its deleted or absent state

#### Scenario: Remote ID is not exact
- **WHEN** deletion is requested using only a date, title, or ambiguous candidate set
- **THEN** the system performs no deletion and requests exact resolution

### Requirement: Disclose and preserve delete tombstones
The system MUST disclose when deleting an externally sourced Intervals.icu activity creates a tombstone and MUST NOT remove that tombstone automatically.

#### Scenario: Garmin-sourced activity is deleted
- **WHEN** preview targets an Intervals.icu activity whose source is Garmin Connect
- **THEN** preview states that deletion creates a tombstone that can prevent automatic re-import

#### Scenario: Application upload is deleted
- **WHEN** preview targets an activity uploaded by this application
- **THEN** preview states that the published behavior deletes it without an external-service tombstone

#### Scenario: Tombstone removal is desired
- **WHEN** a deleted external activity needs to become importable again
- **THEN** tombstone removal remains a separate explicit operation outside automatic reconciliation

### Requirement: Support direct Intervals-only mutations
The system SHALL allow supported create, update, or delete operations to target only Intervals.icu without modifying Garmin, the vault, Weight x Reps, or TrainingPeaks.

#### Scenario: Intervals-only title edit is requested
- **WHEN** the caller selects only Intervals.icu for a supported title update
- **THEN** only the Intervals replica is updated and verified

### Requirement: Return actionable Intervals errors
The system MUST distinguish authentication failure, access denial, rate or transient failure, unsupported source update, not found, ambiguous identity, mutation rejection, and read-back mismatch without leaking credentials.

#### Scenario: API returns access denied
- **WHEN** Intervals.icu returns an authorization failure
- **THEN** the target fails with a redacted actionable authentication error and no other unselected platform is mutated
