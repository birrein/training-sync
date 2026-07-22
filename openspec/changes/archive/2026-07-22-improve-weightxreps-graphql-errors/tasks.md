## 1. Regression Coverage

- [x] 1.1 Add a failing client test proving an HTTP 400 GraphQL `errors` payload is surfaced instead of a generic HTTP error.
- [x] 1.2 Add coverage proving a failed response without a valid GraphQL error payload retains the underlying HTTP error.

## 2. Client Error Handling

- [x] 2.1 Parse GraphQL errors before generic HTTP status handling while preserving 401 refresh and the existing public client behavior.

## 3. Verification

- [x] 3.1 Run focused client tests, the complete test suite, diff checks, and OpenSpec validation.
