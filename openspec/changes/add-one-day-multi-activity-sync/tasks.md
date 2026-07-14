## 1. CLI contract and orchestration preflight
- [x] 1.1 Add failing CLI tests for `sync DATE [--yes]` dispatch and validation.
- [x] 1.2 Add failing use-case tests for zero, one, and multiple activities plus no-write preflight failures.
- [x] 1.3 Implement the minimal CLI and orchestration contract.

## 2. Daily multi-activity rendering
- [x] 2.1 Add failing renderer and vault tests for stable multi-activity replacement and confirmation.
- [x] 2.2 Implement combined rendering and existing-daily replacement.

## 3. Structured Weight x Reps cardio rows
- [ ] 3.1 Add failing parser/domain tests for duration, distance, unit, set type, and comments.
- [ ] 3.2 Implement `type: 1` and `type: 2` JEditor conversion with real fields.
- [ ] 3.3 Add failing mixed-day tests proving strength and every cardio activity are preserved.

## 4. Remote reconciliation and verification
- [ ] 4.1 Add failing client tests for confirmation, full-day replacement, and structured read-back comparison.
- [ ] 4.2 Implement remote replacement and expected-versus-observed verification errors.
- [ ] 4.3 Add orchestration tests proving the daily is retained after a remote failure and retries are idempotent.

## 5. Documentation and end-to-end verification
- [ ] 5.1 Update README usage and remove the obsolete marker-only limitation.
- [ ] 5.2 Run focused tests, the full suite, and a read-only known-day preview.
