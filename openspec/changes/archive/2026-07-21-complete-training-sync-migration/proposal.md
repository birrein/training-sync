## Why

The repository presents itself as Training Sync, but its installed distribution, part of its production implementation, compatibility CLI, editable installation, and local automation references still depend on the former `garmin-sync` identity. Completing the cutover now removes a split identity that makes installation, imports, maintenance, and local operation unnecessarily fragile.

## What Changes

- Move the remaining Garmin adapter implementation and packaged Garmin exercise data from `garmin_sync` into the `training_sync` namespace.
- Update production imports and tests to use only `training_sync` modules.
- **BREAKING** Remove the `garmin-sync` console script and the `garmin_sync` Python package.
- **BREAKING** Remove the hidden legacy CLI forms (`--fetch`, `--weight`, and positional JSON input); retain only the documented `training-sync` command groups.
- Rename the setuptools distribution from `garmin-sync` to `training-sync` and update its project description and release version for the breaking cutover.
- Update current documentation and local operational references to the `training-sync` command and `/Volumes/ssd1/dev/training-sync` checkout.
- Reinstall the editable distribution from the renamed checkout, remove the obsolete installation, and verify that only the new command and package identity remain.
- Preserve the existing `~/.config/training-sync/` credentials and mappings without moving or rewriting secrets.
- Preserve historical Superpowers and archived OpenSpec documents as historical records unless a reference is still operational.

## Capabilities

### New Capabilities

- `training-sync-project-identity`: Defines the canonical distribution, Python namespace, CLI surface, checkout identity, operational references, and cutover verification requirements for Training Sync.

### Modified Capabilities

None. The existing daily multi-activity synchronization and Weight x Reps cardio synchronization requirements remain unchanged.

## Impact

- Affected code: `pyproject.toml`, `src/training_sync/`, removal of `src/garmin_sync/`, and tests that import or assert legacy behavior.
- Affected user interface: removal of the `garmin-sync` executable and undocumented legacy argument forms.
- Affected local environment: editable Python installation, virtual environments, pyenv shims, checkout path, Codex project configuration, and the personal Garmin-to-Obsidian skill.
- Unaffected persisted state: Garmin and Weight x Reps tokens, exercise mappings, Weight x Reps user id, Obsidian content, and remote training records.
- Repository remote: already uses `https://github.com/birrein/training-sync.git`; no remote rename is required.
