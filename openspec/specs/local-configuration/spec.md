# local-configuration Specification

## Purpose
Define how Training Sync stores and resolves machine-specific local
configuration without personal defaults or versioned secrets.
## Requirements
### Requirement: Centralize persistent local configuration

Training Sync MUST store persistent machine-specific configuration under
`~/.config/training-sync/` and MUST keep personal filesystem paths out of
versioned source files.

#### Scenario: Local configuration files are resolved centrally

- **WHEN** a setting needs persistent machine-specific state
- **THEN** its local file is resolved beneath `~/.config/training-sync/` rather
  than from a repository-relative or personal hardcoded path

### Requirement: Prefer non-empty environment overrides

Settings using the local configuration convention MUST prefer a non-empty
environment variable over the corresponding local file and MUST read the local
file when no non-empty override is present.

#### Scenario: Environment override wins

- **WHEN** both an environment value and a local file contain a vault root
- **THEN** the environment value is used and the local file is not selected

#### Scenario: Local file is used without an override

- **WHEN** the environment variable is unset or blank and the local file exists
- **THEN** the trimmed local file value is used

### Requirement: Separate local value classes

Training Sync MUST keep credentials, tokens, and API keys separate from ordinary
IDs/mappings and filesystem paths, and MUST NOT require any of those local values
to be committed to the repository.

#### Scenario: Local values remain classified

- **WHEN** a user configures a token/API key, an ID/mapping, and a vault path
- **THEN** each value is stored in its documented local file class under the
  central configuration directory and no secret or personal path is versioned

### Requirement: Validate required vault configuration early

Vault-backed commands MUST reject missing, blank, or non-absolute vault
configuration with an actionable error before loading provider tokens or
constructing provider clients.

#### Scenario: Vault configuration is absent

- **WHEN** `TRAINING_SYNC_VAULT_ROOT` and the local `vault-root` file are absent
  or blank
- **THEN** the command stops and identifies the environment variable and local
  file as the configuration actions

#### Scenario: Vault configuration is relative

- **WHEN** the selected vault value is a relative path
- **THEN** the command stops with an absolute-path validation error before any
  provider client is created
