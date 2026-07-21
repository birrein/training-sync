## Context

Training Sync already has the public product identity and most of its architecture: the Git remote is named `training-sync`, the README documents `training-sync`, runtime configuration lives under `~/.config/training-sync/`, and the integrated Garmin-to-Obsidian-to-Weight-x-Reps flow is implemented in `training_sync`.

The cutover is incomplete because the setuptools distribution is still named `garmin-sync`, both console scripts are installed, `training_sync.cli` imports Garmin behavior from `garmin_sync`, legacy argument forms remain accepted, and the editable installation and local operational tooling point to `/Volumes/ssd1/dev/garmin-sync`. The current test baseline is 218 passing tests when the source tree is made importable explicitly.

This is a cross-cutting, intentionally breaking migration. Repository implementation must complete before machine-level references and the checkout path are changed.

## Goals / Non-Goals

**Goals:**

- Make `training-sync` the sole distribution, Python namespace, console command, current documentation identity, and local checkout identity.
- Move all remaining Garmin adapter behavior and package data under `training_sync` without changing synchronization semantics.
- Remove compatibility-only code and tests rather than retaining indefinite wrappers.
- Preserve `~/.config/training-sync/` tokens, mappings, and user-id state unchanged.
- Provide a staged cutover with explicit verification and rollback points.
- Finish with a clean installation whose metadata and commands do not expose `garmin-sync`.

**Non-Goals:**

- Change Garmin, Obsidian, or Weight x Reps synchronization behavior.
- Change the daily-note format, confirmation rules, exercise resolution, or read-back verification contract.
- Migrate credentials or rewrite secret-bearing configuration files.
- Rewrite historical Superpowers plans/specs or archived OpenSpec changes solely to remove old names.
- Adopt a different Python build backend or dependency manager as part of this identity migration.

## Decisions

### 1. Move Garmin behavior into a dedicated `training_sync.garmin` package

The remaining production modules will move to a cohesive adapter package:

```text
src/training_sync/garmin/
  __init__.py
  auth.py
  fetch.py
  weight.py
  import_strength.py
  payloads.py
  exercise_mapping.py
  garmin_exercises.json
```

`training_sync.domain.strength_workout` remains the canonical strength domain model. Production imports and tests will target the new modules directly. Once no live imports remain, `src/garmin_sync/` will be deleted.

This preserves the existing modular architecture and makes Garmin one adapter alongside `vault` and `weightxreps`. The alternative of leaving `garmin_sync` as an internal implementation package was rejected because it would keep the split identity permanently. A one-file compatibility wrapper was also rejected because the requested cutover is definitive rather than transitional.

### 2. Expose only the modern CLI contract

`pyproject.toml` will declare the `training-sync` distribution and only the `training-sync = "training_sync.cli:main"` console script. The release version will become `1.0.0` to mark the breaking public-identity cutover.

The parser will accept only the documented `sync`, `garmin`, and `weightxreps` command groups. Hidden `--fetch`, `--weight`, positional JSON handling, and the handler indirection used by the legacy wrapper will be removed. Strength JSON import remains available through `training-sync garmin import-strength FILE`.

Retaining deprecated aliases for another release was considered, but rejected because this is a personal local tool, the replacement commands already work, and carrying both identities is the problem being resolved.

### 3. Treat repository migration and machine cutover as separate gates

Repository work will be completed and verified while the checkout still has its old path. Only after the new package passes tests and clean-install checks will operational references be updated and the directory renamed.

The OpenSpec implementation is repo-local. Machine-level changes outside the repository, including Codex configuration, the personal Garmin synchronization skill, pyenv installation, and the physical directory rename, form an explicit post-implementation cutover gate. They must be performed deliberately after repository verification rather than hidden inside source refactoring.

### 4. Preserve current configuration state in place

No token or mapping migration is required because all active state already lives under `~/.config/training-sync/`. The cutover will verify that the new installation resolves those same paths. It will not inspect, print, copy, or rewrite token contents.

The obsolete editable distribution will be removed only after a new editable installation from `/Volumes/ssd1/dev/training-sync` succeeds. This provides a simple rollback path while avoiding a period with no working command.

### 5. Keep historical records historically accurate

README and other current operational instructions will use only the new identity. Historical plans, design specs, archived changes, and retrospectives may retain paths and commands that were correct when written. Verification searches will therefore distinguish live source/current documentation from historical archives rather than requiring a repository-wide zero-match result.

## Risks / Trade-offs

- **Breaking local scripts or muscle memory** → Update the known Codex skill and current documentation during cutover; verify the modern replacements before removing the old installation.
- **Editable installation breaks when the directory moves** → Complete repository verification first, rename the checkout last, then reinstall immediately from the new absolute path.
- **Module moves accidentally change Garmin behavior or omit package data** → Move code test-first, keep behavior-focused tests, verify `garmin_exercises.json` is included in the installed distribution, and run the complete suite.
- **Tests pass only because the source checkout is on `PYTHONPATH`** → Add a clean temporary-environment installation test and inspect installed distribution metadata and entry points.
- **Historical references create false migration failures** → Scope zero-legacy-reference checks to production code, tests, packaging metadata, README, and live operational files; explicitly exempt historical artifacts.
- **External machine configuration is edited before the repository is safe** → Use a separate cutover gate after repository commits and verification.
- **Current unpushed work is lost or mixed into the migration** → Preserve the existing ahead commit, start the migration on `refactor/project-training-sync-cutover`, and inspect status/history before any move.

## Migration Plan

1. Record preflight state: clean worktree, current branch/ahead status, remote URL, installed editable path, CLI help, and 218-test baseline.
2. Create `refactor/project-training-sync-cutover` without rewriting the existing local commit.
3. Add or update tests so canonical imports and CLI expectations use only `training_sync`; remove tests whose sole contract is legacy compatibility.
4. Move Garmin implementation and package data to `training_sync.garmin`, update imports, then delete `src/garmin_sync/`.
5. Change distribution metadata to `training-sync` version `1.0.0`, retain only the modern console entry point, and remove compatibility parser/handler code.
6. Update README and other current repository documentation while preserving historical artifacts.
7. Run focused tests, the full suite, package-data checks, and a clean temporary editable-install verification. Confirm `training-sync --help` works and the installed distribution exposes no `garmin-sync` entry point or `garmin_sync` import.
8. Commit and push the verified repository migration before changing machine-level paths.
9. At the explicit machine-cutover gate, update known live references in Codex configuration and the Garmin-to-Obsidian skill, rename the checkout to `/Volumes/ssd1/dev/training-sync`, uninstall the obsolete editable distribution, install `training-sync` from the new path, and refresh pyenv shims.
10. Reopen the project from the new checkout and run final smoke checks, including a read-only Garmin command and config-path resolution. A real mutating day sync is optional and must retain its existing confirmation and read-back safeguards.

Rollback before the machine cutover is a normal Git revert or branch reset that preserves the existing main branch. Rollback after the directory rename consists of renaming the checkout back, reinstalling the previous `garmin-sync` commit in editable mode, restoring the two known local references, and refreshing shims. Persisted tokens and remote training data remain untouched in either path.

## Open Questions

None required before implementation. The cutover deliberately chooses the breaking `1.0.0` identity, retains the existing build backend, and defers machine-level mutations until the repository is verified.
