## 1. Preflight and Isolation

- [x] 1.1 Confirm the worktree is clean apart from this change, preserve the existing `main` commit that is ahead of `origin/main`, and record the remote URL, editable-install path, CLI help, and 218-test baseline.
- [x] 1.2 Create and switch to `refactor/project-training-sync-cutover` without rewriting or dropping the existing local commit.

## 2. Canonical Garmin Package

- [x] 2.1 Add failing tests that import the planned `training_sync.garmin` modules and load the packaged `garmin_exercises.json`; run the focused tests and confirm the expected failures before production changes.
- [x] 2.2 Create `training_sync.garmin` and move authentication plus body-weight behavior into it; update the focused tests/imports and run them to green.
- [x] 2.3 Move Garmin activity fetching, strength import, payload construction, exercise mapping, and package data into `training_sync.garmin`; update their focused tests/imports and run them to green.
- [x] 2.4 Update `training_sync.cli` and synchronization dependencies to use only `training_sync.garmin`, then run the CLI, Garmin, and sync use-case tests.
- [x] 2.5 Update remaining behavior tests to canonical imports, delete compatibility-only tests and `src/garmin_sync/`, and verify that live source and tests contain no `garmin_sync` imports.

## 3. Distribution and CLI Cutover

- [x] 3.1 Add failing tests for the canonical modern command surface and rejection of `--fetch`, `--weight`, and positional JSON without constructing clients or performing writes.
- [x] 3.2 Remove legacy parser branches, the compatibility handler context, and the `garmin-sync` wrapper entry point; run the focused CLI tests to green.
- [x] 3.3 Rename the distribution to `training-sync`, set version `1.0.0`, update the project description, and declare only `training-sync = "training_sync.cli:main"` in `pyproject.toml`.
- [x] 3.4 Add an installed-metadata test or equivalent clean-environment assertion proving that the distribution and console entry point use only the canonical identity.

## 4. Current Documentation

- [x] 4.1 Update README installation, strength-import examples, source paths, and current terminology to use only `training-sync` and `training_sync`.
- [x] 4.2 Search live repository code, packaging, tests, README, and operational instructions for legacy names; remove operational matches while preserving explicitly historical Superpowers and archived OpenSpec references.

## 5. Repository Verification

- [x] 5.1 Run focused Garmin, CLI, package-data, and synchronization tests and fix any migration regressions without changing the existing synchronization contracts.
- [x] 5.2 Run the complete test suite from the intended project environment and confirm all non-legacy behavior tests pass.
- [x] 5.3 Install the project into a clean temporary environment and verify distribution metadata, packaged Garmin exercise data, `training-sync --help`, absence of the `garmin-sync` entry point, and failure to import `garmin_sync`.
- [x] 5.4 Inspect `git diff --check`, status, and the complete migration diff; confirm tokens, mappings, vault notes, and remote training data were not touched.
- [ ] 5.5 Commit the verified repository migration with Conventional Commits and push the migration branch before beginning the machine-level cutover.

## 6. Explicit Machine Cutover Gate

- [ ] 6.1 After repository verification and explicit cutover confirmation, update the known Codex project configuration and Garmin-to-Obsidian skill to use `/Volumes/ssd1/dev/training-sync` and modern `training-sync` commands.
- [ ] 6.2 Rename `/Volumes/ssd1/dev/garmin-sync` to `/Volumes/ssd1/dev/training-sync` only after validating both exact paths and ensuring the destination does not already exist.
- [ ] 6.3 Remove the obsolete editable `garmin-sync` distribution, install `training-sync` in editable mode from the new checkout, refresh pyenv shims, and verify command resolution points to the new path.
- [ ] 6.4 Reopen the project from `/Volumes/ssd1/dev/training-sync` and verify `training-sync --help`, absence of `garmin-sync`, canonical configuration paths, and one read-only Garmin command.
- [ ] 6.5 Record final cutover evidence and rollback instructions without exposing token or credential contents.
