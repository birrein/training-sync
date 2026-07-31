## 1. uv tool behavior evidence

- [x] 1.1 Inspect local help for `uv tool install`, `uv tool upgrade`, `uv tool dir`, and `uv tool update-shell`.
- [x] 1.2 Validate non-editable installation and direct execution from outside the checkout in isolated temporary tool directories.
- [x] 1.3 Validate editable checkout binding, `--force` reinstall, and `uv tool upgrade` behavior without touching the user's real uv tool directory.

## 2. Operational documentation

- [x] 2.1 Document persistent non-editable installation, PATH setup, and explicit `--force` updates with neutral paths.
- [x] 2.2 Use direct `training-sync ...` for operational examples while retaining `uv run` for development/testing.
- [x] 2.3 Document editable limitations and preserve local credential/provider configuration boundaries.

## 3. Delivery

- [x] 3.1 Run strict OpenSpec validation, full uv test suite, CLI smoke test, and `git diff --check`.
- [x] 3.2 Complete `verify.md`, `retrospective.md`, archive the change, and confirm stable spec synchronization.
- [x] 3.3 Create one Conventional Commit containing only this documentation/spec change; do not push.
