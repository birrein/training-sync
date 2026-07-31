## 1. Project dependency and lock setup

- [x] 1.1 Add the standard development dependency group with pytest while preserving `[project].dependencies` and `requires-python = ">=3.10"`.
- [x] 1.2 Generate `uv.lock` with `uv lock` and confirm the lock contains no credentials, vault paths, or provider state.
- [x] 1.3 Run `uv sync --locked` and `uv run pytest -q`; confirm the environment and full suite work from the lock.

## 2. Developer documentation

- [x] 2.1 Replace the primary README venv/pip installation path with `uv sync --dev` and document the uv prerequisite.
- [x] 2.2 Document `uv run training-sync ...`, `uv run pytest -q`, `uv lock`, and `uv sync --locked` without changing local configuration/authentication guidance.

## 3. Final safety validation

- [x] 3.1 Run the complete test suite, locked synchronization, CLI help smoke test, `git diff --check`, and inspect the diff for credential/provider changes.
- [x] 3.2 Commit only the uv migration files with a Conventional Commit; do not modify credentials, provider state, or unrelated branches.
