## Context

`WeightxRepsClient.graphql()` currently calls `response.raise_for_status()` before decoding the JSON response. Weight x Reps includes GraphQL validation errors in the JSON body of HTTP 400 responses, so that ordering replaces actionable API diagnostics with a generic `requests.HTTPError`.

## Goals / Non-Goals

**Goals:**

- Surface GraphQL error payloads regardless of whether the HTTP status is successful or failed.
- Preserve token refresh on HTTP 401 and generic HTTP handling when the body is not a GraphQL error response.
- Keep the public client methods and dependencies unchanged.

**Non-Goals:**

- Introduce a GraphQL client library or schema/code generation.
- Change authentication, retries, synchronization preflight, or write behavior.
- Modify remote or local training data during verification.

## Decisions

- Decode the final response body before generic HTTP status handling. If it is a JSON object containing a non-empty `errors` field, raise `RuntimeError` with those server details; otherwise retain `raise_for_status()`.
- Treat invalid or non-object JSON as an ordinary HTTP response. The client will preserve the existing `requests` exception rather than replace it with a JSON decoding or attribute error.
- Test both the GraphQL-error path and the non-GraphQL HTTP fallback through the existing fake session boundary. This verifies observable client behavior without adding test-only production seams.

## Risks / Trade-offs

- **Risk:** An error body is not valid JSON. **Mitigation:** Fall back to the original HTTP status exception.
- **Risk:** A JSON error response has an unexpected top-level shape. **Mitigation:** Only interpret dictionary payloads with a non-empty `errors` field as GraphQL errors.
- **Trade-off:** The raised exception remains `RuntimeError` for compatibility rather than introducing a new public exception hierarchy.
