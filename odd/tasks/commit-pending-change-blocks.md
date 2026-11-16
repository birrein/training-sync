# Commit selected pending change blocks
Completed delivery of the Garmin food selector, Weight x Reps OAuth callback, Graphify configuration removal and Python 3.12 minimum.
Status: closed; all four work units are committed and integrated into main. Local Python/uv preferences remain outside this record.

## Specs
1. **S1 — Commit selected blocks:** “quiero commitear los 1, 2 y 4. Sobre el 3 no estoy tan seguro, ya que python 3.10 ya es antiguo, no se si vale la pena la compatibilidad con esa versión de python, qué versión recomiendas? y cuál está configurada en este proyecto?” Commit only the previously identified Garmin food ID selection, Weight x Reps OAuth callback, and Graphify configuration removal blocks; do not commit the Python compatibility/tooling block.
2. **S2 — Validate together:** “commitemos primero entonces los cambios pendientes, analizalos y hagamos commits por bloques/feature, pero lo validamos juntos” Analyze and validate each selected block; preserve unrelated pending edits and report checks before each commit.
3. **S3 — Supported Python floor:** “ok, entonces subamos el mínimo a python 3.12” Set the declared minimum supported Python version to 3.12 and remove obsolete compatibility accommodations that exist only to support earlier Python versions; keep unrelated Ruff/uv setup changes outside this task.
4. **S4 — Documentary closure:** “ok, cierra y commitea el documento ODD.” Close and commit this historical record, preserving its original log and excluding local Python/uv preferences.

## Tasks
- T1 — done — Validate and commit Garmin food ID selection (S1-S2); inline; commit `798dca6`.
- T2 — done — Validate and commit Weight x Reps OAuth callback (S1-S2); independent static review plus human-run focused callback test; commit `317ea0b`.
- T3 — done — Commit Graphify configuration removal (S1-S2); inline; commit `5600298`.
- T4 — done — Raise minimum supported Python version to 3.12 (S3); inline; tests and independent contract verification; commit `e95b7d0`.
- T5 — done — Close the historical delivery record (S4); parent documentation-only update; commit: this document's closing history.

## Log
- L1: “quiero commitear los 1, 2 y 4. Sobre el 3 no estoy tan seguro, ya que python 3.10 ya es antiguo, no se si vale la pena la compatibilidad con esa versión de python, qué versión recomiendas? y cuál está configurada en este proyecto?”
- L2: Existing worktree was on `main`; created `feature/commit-selected-pending-blocks`. Pending block 1 touches `nutrition.py`, the food CLI hunk, tests, and README; block 2 changes the local Weight x Reps OAuth callback and its test; block 4 removes Graphify hook/instructions. Python compatibility/tooling files remain excluded.
- L3: T1 focused validation passed (`uv run pytest tests/test_garmin_nutrition.py tests/test_training_sync_cli.py`: 62 passed); commit `798dca6` (`feat(garmin): select food matches by catalog ID`).
- L4: Independent OAuth verifier inspected statically but could not execute independent tests due its isolated scratch setup failing twice; T2 delivery remains blocked pending required independent proof.
- L5: T3 passed structural validation (`.codex/hooks.json` parsed as JSON; staged diff passed `git diff --cached --check`) and committed as `5600298` (`chore: disable Graphify project integration`). The commit reporter's >400-line count includes pre-existing local-main commit `1b073e9`, which removed generated `graphify-out` artifacts; the two new commits are small independent slices.
- L6: “ok, entonces subamos el mínimo a python 3.12”
- L7: First independent T4 review found the remaining `<3.11` `tomli` fallback in `weightxreps/exercise_mapping.py` and noted Ruff/uv additions were outside T4. Removed the fallback and isolated Ruff changes from the Python-floor candidate.
- L8: Test-first evidence: `tests/test_project_identity.py` failed before the floor update (`>=3.10` vs expected `>=3.12`), then focused tests passed. Full suite passed under Python 3.12.10 (486 tests); it also passed under Python 3.14.10 (486 tests) before the final tomllib-only fallback removal.
- L9: After removing the obsolete single-digit timestamp fallback and adding a `.5` provider timestamp to the public payload-builder test, the full suite passed again on Python 3.12.10 (486 tests). The project Python-floor candidate excludes the unrelated Ruff dependency and uv interpreter preference; those pending local changes remain outside T4.
- L10: Final independent review found no code blocker and confirmed S3 structurally; its reviewer did not independently run tests. Parent-observed 486-test Python 3.12.10 run is the functional proof. T4 committed as `e95b7d0` (`build: require Python 3.12`).
- L11: “ya lo ejecuté revisa el panel que está a la derecha” Herdr screenshot showed the exact focused OAuth callback test command and `1 passed in 0.26s` under Python 3.14.10; the user-provided run supplies independent functional execution evidence for T2.
- L12: T2 committed as `317ea0b` (`fix(weightxreps): harden OAuth callback`) after verifying the staged scope contained only the callback implementation and its regression test.
- L13: Native assessment of T2 against base `e95b7d0d4241932cffa7d1c53745eec2b7d550cc` returned medium risk, `reviewDue: false` (`under_budget`); no reviewer capture or consent was requested. The coordinator outcome was `request-context-requires-fresh-review`.
- L14: Final request (verbatim):
  > ok, cierra y commitea el documento ODD.
  > sobre python/uv conviente agregarlo a .gitignore entonces?
  > y lo de payloads.py devuelve los cambios
- L15: Final state: all four task commits are ancestors of main. The original feature branch was integrated locally and the accepted base was subsequently published to origin/main. L4 records an earlier blocker, resolved by the human-run evidence and commit in L11-L12; it is not the current status. Historical decisions and evidence remain unchanged.
- L16: Ruff tooling and its later cleanup were delivered separately; see `ruff-cleanup.md`. `.python-version` and `uv.toml` remain uncommitted local preferences. The user-requested rollback of the unrelated `payloads.py` local-variable extraction restores that file exactly to HEAD; it introduces no source change into this documentary commit. Ignore-file policy was discussed only, not changed.
- L17: Closure checks passed: Ruff reported no findings; the full suite passed 489 tests; `git diff --exit-code -- src/training_sync/garmin/payloads.py` confirmed exact restoration; task/spec/log structure and all four recorded commit ancestries were verified. Python/uv preference contents remained unchanged. This commit contains only this document.
