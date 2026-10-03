## 1. Garmin Nutrition adapter

- [x] 1.1 Add mocked response fixtures and failing tests in `tests/test_garmin_nutrition.py` for exact food/serving matching, amount conversion, enabled meal windows (including overnight), locale/source preservation, and duplicate rejection; verify RED with `python -m pytest tests/test_garmin_nutrition.py -q`.
- [x] 1.2 Implement request construction and safe preflight in `src/training_sync/garmin/nutrition.py`; verify the focused tests pass and assert no PUT occurs on ambiguous, invalid, or duplicate inputs.
- [x] 1.3 Add failing tests for single-batch PUT payloads and success, rejected, timeout/uncertain, partial-readback outcomes; verify RED with the focused pytest command.
- [x] 1.4 Implement single-write reconciliation and strict GET verification in `src/training_sync/garmin/nutrition.py`; verify focused tests pass and uncertain outcomes never trigger a second PUT.

## 2. User command and project verification

- [x] 2.1 Add failing parser/dispatch tests in `tests/test_training_sync_cli.py` for `garmin food-log DATE TIME --item NAME=QUANTITY`; verify RED with `python -m pytest tests/test_training_sync_cli.py -q`.
- [x] 2.2 Add the command to `src/training_sync/cli.py`, reusing `get_client()` and printing verified result fields; verify the focused CLI tests pass.
- [x] 2.3 Document preview and explicit apply usage in `README.md`; verify examples match CLI help.
- [x] 2.4 Run `uv run pytest -q` and `openspec validate add-garmin-nutrition-logging --strict`; record any environment-specific limitations and mark completed tasks only after their checks pass.
