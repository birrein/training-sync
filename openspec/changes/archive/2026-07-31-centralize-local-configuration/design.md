## Context

The current project centralizes local files in `~/.config/training-sync/`.
Before `789b6fe`, the CLI embedded a personal absolute vault path. The merged
implementation introduced `vault_root_path()`, `_load_local_setting()`, and
early CLI validation, while retaining existing token, mapping, and user-ID
paths. The later feature integration also has a separate `intervals-api-key`
local secret path; this retrospective records its classification but does not
claim that commit refactored it through the common helper.

## Goals / Non-Goals

**Goals:**

- Make the local configuration directory and value classes explicit.
- Preserve env-over-local precedence for the vault and user ID.
- Specify missing and invalid vault configuration behavior.
- Prevent personal machine paths and secrets from entering version control.

**Non-Goals:**

- Changing the already-integrated runtime implementation.
- Migrating or reading real credentials, API keys, or vault files.
- Contacting Garmin, Weight x Reps, Intervals.icu, or any other provider.
- Claiming that every existing secret loader was refactored in `789b6fe`.

## Decisions

### D1: One persistent local configuration directory

- **Choice**: Use `~/.config/training-sync/` for machine-specific files.
- **Reason**: This directory already contains tokens and mappings and keeps
  local state outside the repository.
- **Alternative considered**: Add per-option files beside source code; rejected
  because that would distribute machine state and invite accidental commits.

### D2: Environment override before local file

- **Choice**: A non-empty environment value wins; otherwise read the local
  file. Blank environment values are treated as absent for settings using the
  common loader.
- **Reason**: CI, shells, and different machines can override safely without
  editing persistent files.
- **Alternative considered**: Use only environment variables; rejected because
  persistent local configuration is already an established project pattern.

### D3: Validate vault configuration before provider setup

- **Choice**: Require an absolute vault path and fail before token loading or
  client construction when neither source is valid.
- **Reason**: Configuration errors are local and actionable, and must not cause
  unnecessary provider interaction.
- **Alternative considered**: Fall back to a default path; rejected because it
  couples the project to one personal machine.

### D4: Classify values by sensitivity and purpose

- **Choice**: Keep credentials/tokens/API keys, IDs/mappings, and filesystem
  paths in distinct named files under the same directory; never version secrets
  or personal paths.
- **Reason**: Clear ownership and sensitivity reduce accidental disclosure.
- **Alternative considered**: One checked-in config file; rejected because it
  mixes secrets and machine-specific paths with project code.

## Risks / Trade-offs

- [Risk] A missing local file can stop vault-backed commands → Mitigation:
  provide the exact environment variable and file path in the error and README.
- [Risk] A future setting may bypass the convention → Mitigation: require its
  env name, local filename, precedence, validation, and absence behavior in its
  spec and documentation.
- [Trade-off] Local configuration is not portable by itself → Accepted because
  portability is achieved by per-machine values, not personal defaults.

## Migration Plan

N/A for runtime migration. The implementation is already on `main` in `789b6fe`;
this change archives the contract and synchronizes its stable spec. No local
files are created or modified by this documentation cycle.

## Open Questions

None for this retrospective scope. Future secret loaders should adopt the same
precedence helper when their runtime behavior is changed deliberately.
