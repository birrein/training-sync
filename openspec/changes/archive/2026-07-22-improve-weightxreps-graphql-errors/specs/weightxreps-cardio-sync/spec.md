## ADDED Requirements

### Requirement: Surface Weight x Reps GraphQL errors

The system MUST preserve actionable GraphQL error details returned by Weight x Reps, including when the response has a failed HTTP status, and MUST retain generic HTTP failure behavior when no GraphQL error payload is available.

#### Scenario: Failed HTTP response contains GraphQL errors
- **WHEN** Weight x Reps returns an HTTP 400 response with a GraphQL `errors` payload
- **THEN** synchronization fails with the GraphQL error details
- **AND** the generic HTTP status error does not hide those details

#### Scenario: Failed HTTP response lacks GraphQL errors
- **WHEN** Weight x Reps returns a failed HTTP response without a valid GraphQL `errors` payload
- **THEN** synchronization fails with the underlying HTTP status error
