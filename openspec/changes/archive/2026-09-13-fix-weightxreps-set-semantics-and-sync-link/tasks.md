## 1. Regression Coverage

- [x] 1.1 Add a failing JEditor regression test in `tests/test_weightxreps_jeditor.py` for mixed repetition counts and require one physical row per distinct set.
- [x] 1.2 Add failing JEditor regression tests in `tests/test_weightxreps_jeditor.py` for RPE/RIR-derived effort on a non-final set and on a consolidated line.
- [x] 1.3 Add failing Weight x Reps client and CLI tests in `tests/test_weightxreps_client.py` and `tests/test_training_sync_cli.py` for authenticated username lookup, journal URL construction, and successful output.
- [x] 1.4 Run the focused regression suite before production edits and confirm that the new expectations fail for the old implementation.

## 2. Weight x Reps Implementation

- [x] 2.1 Update `src/training_sync/weightxreps/jeditor.py` to validate strength-set semantics before building rows, reject mixed repetitions, and require effort annotations on the final single physical set.
- [x] 2.2 Update `src/training_sync/weightxreps/client.py` to read the authenticated username and construct the URL-escaped journal URL for a requested date.
- [x] 2.3 Update `src/training_sync/cli.py` to include `weightxreps_url` in successful `sync DATE` and `weightxreps push DATE` JSON output after the use case's save and read-back verification.
- [x] 2.4 Keep the implementation limited to the affected Weight x Reps code and tests; do not alter unrelated pre-existing worktree changes.

## 3. Verification and Handoff

- [x] 3.1 Run `python -m pytest tests/test_weightxreps_jeditor.py tests/test_weightxreps_client.py tests/test_training_sync_cli.py -q` and confirm the focused suite passes.
- [x] 3.2 Run `python -m pytest -q` and confirm the complete repository suite passes.
- [x] 3.3 Run `git diff --check` and confirm there are no whitespace errors.
- [x] 3.4 Run `openspec validate --all --strict --no-interactive` and confirm the change artifacts and repository specs validate.
- [x] 3.5 Conventional Commit checkpoint: the affected implementation is ready to commit as `fix(weightxreps): preserve set semantics and direct journal link`; unrelated dirty files remain outside this change.
