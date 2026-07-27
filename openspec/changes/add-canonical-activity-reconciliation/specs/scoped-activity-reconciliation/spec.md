## ADDED Requirements

### Requirement: Select mutation targets exactly
The system MUST construct an explicit synchronization scope from the platforms named by the caller and MUST NOT mutate an unselected platform.

#### Scenario: Two destinations are selected
- **WHEN** the caller selects only the vault and Weight x Reps
- **THEN** the plan contains operations only for those destinations and does not mutate Garmin, Intervals.icu, or TrainingPeaks

#### Scenario: All configured destinations are selected
- **WHEN** the caller explicitly selects all compatible configured destinations
- **THEN** the plan includes every compatible destination and reports any configured adapter that lacks the required capability

#### Scenario: Target instruction is ambiguous
- **WHEN** a mutating request does not identify a safe exact scope
- **THEN** the system produces a preview or clarification result and performs no mutation

### Requirement: Preserve the existing default synchronization scope
The system SHALL preserve the existing `sync DATE` behavior for the vault and Weight x Reps and MUST NOT silently add a newly configured provider to that default scope.

#### Scenario: Intervals credentials are added
- **WHEN** Intervals.icu is configured and the caller runs the existing `sync DATE` command without selecting new targets
- **THEN** the existing vault and Weight x Reps behavior is preserved and Intervals.icu is not mutated

### Requirement: Support provider-local editing without propagation
The system SHALL allow a supported mutation to target exactly one provider replica without automatically propagating it to the canonical source or other replicas.

#### Scenario: Weight x Reps-only correction is requested
- **WHEN** the caller requests a supported correction only in Weight x Reps
- **THEN** the system plans and applies only the Weight x Reps operation

#### Scenario: Later reconciliation observes the correction
- **WHEN** a later canonical reconciliation finds that provider-local state differs from the canonical projection
- **THEN** the difference is shown as a conflict or proposed overwrite and is not silently replaced

### Requirement: Plan mutations before applying them
The system MUST read and validate all required source, identity, target, capability, confirmation, and payload information and SHALL produce a deterministic reconciliation plan before its first mutation.

#### Scenario: Plan contains a deletion
- **WHEN** reconciliation proposes deleting a duplicate replica
- **THEN** preview identifies the provider, remote ID, local start, title, match reason, destructive consequence, and replica to retain

#### Scenario: Preflight finds an ambiguous exercise
- **WHEN** exercise resolution is ambiguous for any selected target
- **THEN** planning fails before any selected platform is mutated

### Requirement: Require explicit authorization to apply a plan
The system MUST default to preview and MUST require explicit confirmation to apply the exact displayed plan.

#### Scenario: Confirmation is absent
- **WHEN** a plan contains create, update, or delete operations and authorization is absent
- **THEN** the system reports the plan and performs no mutation

#### Scenario: Confirmation is present
- **WHEN** the caller explicitly authorizes the displayed plan
- **THEN** the system may apply only the operations and targets contained in that plan

### Requirement: Revalidate remote state before mutation
The system MUST retain an observed target fingerprint in the plan and MUST stop that target when its remote state changes before application.

#### Scenario: Replica changes after preview
- **WHEN** a selected replica's relevant remote fields no longer match the observed plan fingerprint
- **THEN** the target fails without mutation and the system requires a fresh plan

### Requirement: Use only capabilities supported by each adapter
The system MUST resolve the required read, create, update, delete, source-artifact, and verification capabilities before applying a target operation.

#### Scenario: Selected adapter cannot update
- **WHEN** a plan requires an update but the selected adapter or remote source type does not support updates
- **THEN** the operation fails during planning and no mutation is attempted for that target

### Requirement: Protect Garmin from downstream reconciliation
The system MUST NOT delete or replace Garmin through a destination reconciliation plan.

#### Scenario: Destination duplicate is removed
- **WHEN** a duplicate destination replica refers to a Garmin canonical activity
- **THEN** deletion can target the destination replica but cannot target Garmin

#### Scenario: Garmin merge is requested
- **WHEN** multiple Garmin recordings need to be joined or replaced
- **THEN** the system requires a separate explicit Garmin workflow that verifies the replacement before deleting authorized originals

### Requirement: Verify each applied target independently
The system MUST read each mutated target back and compare its supported expected state before reporting that target as successful.

#### Scenario: Saved target matches
- **WHEN** a target's read-back matches the expected supported fields
- **THEN** the target result is `verified`

#### Scenario: Saved target differs
- **WHEN** a write returns success but read-back differs from the expected state
- **THEN** the target result is `failed` and overall reconciliation is not reported as fully successful

### Requirement: Report partial outcomes without fictitious rollback
The system SHALL report each selected target as `verified`, `failed`, or `not_attempted` and MUST preserve already verified target writes when another independent target fails.

#### Scenario: Second destination fails
- **WHEN** the vault and Weight x Reps verify successfully but Intervals.icu fails
- **THEN** the successful writes remain, Intervals.icu is reported failed, later unattempted targets are identified, and the command returns a non-success partial result

### Requirement: Retry reconciliation idempotently
The system SHALL rebuild a plan from current canonical and remote state so a retry can skip already verified targets and operate only on remaining drift.

#### Scenario: Partial result is retried
- **WHEN** a prior run verified Weight x Reps and failed Intervals.icu
- **THEN** the new plan treats matching Weight x Reps state as a no-op and proposes only the still-required Intervals.icu operation
