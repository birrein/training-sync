## 1. Regression Coverage

- [x] 1.1 Add a failing Weight x Reps client test that requires the exercise-catalog query to declare `$uid` as `ID!`, sends the configured identifier, and parses exercises nested under each returned `ExerciseStat.e`.

## 2. Client Compatibility Fix

- [x] 2.1 Update the exercise-catalog GraphQL declaration and nested response parsing without changing configuration or public client behavior, then run the focused client tests.

## 3. Verification

- [x] 3.1 Run the complete test suite and OpenSpec validation.
- [x] 3.2 Perform a read-only live complete-catalog lookup with the configured user id and confirm that `Cycling` resolves to exercise id `157740` without modifying remote training data.
