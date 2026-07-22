## ADDED Requirements

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
