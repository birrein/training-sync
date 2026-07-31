## ADDED Requirements

### Requirement: Preserve Python compatibility in the locked project

The project MUST retain `requires-python = ">=3.10"`, MUST keep runtime
dependencies declared in `pyproject.toml`, and MUST commit a `uv.lock` that is
generated from that metadata.

#### Scenario: Python 3.10+ environment is synchronized

- **WHEN** a developer runs the documented uv synchronization command on a
  supported Python 3.10-or-newer environment
- **THEN** uv resolves the project from `pyproject.toml` and the committed lock
  without lowering the declared Python floor

### Requirement: Declare development dependencies separately

The project MUST declare test-only dependencies in a development dependency
group and MUST make that group available through the documented development
sync command without adding test packages to runtime dependencies.

#### Scenario: Development environment includes pytest

- **WHEN** a developer runs `uv sync --dev`
- **THEN** the project environment contains the declared test dependencies and
  the runtime dependency list remains limited to runtime packages

### Requirement: Provide locked development and test commands

The README MUST document `uv sync --dev`, `uv run`, `uv run pytest -q`,
`uv lock`, and `uv sync --locked` as the supported project workflow, and MUST
not require a manually activated venv or pip install for the primary path.

#### Scenario: Fresh developer setup

- **WHEN** a developer follows the installation instructions on another
  machine
- **THEN** they can create the project environment, run the CLI, and run the
  test suite through uv using the committed lockfile

#### Scenario: Lock drift is detected

- **WHEN** `pyproject.toml` and `uv.lock` are out of sync
- **THEN** `uv sync --locked` fails instead of silently rewriting the lock

### Requirement: Keep dependency setup separate from local and provider state

uv setup MUST remain provider-isolated and MUST NOT require, read, write, or version
Garmin, Weight x Reps, Intervals.icu, vault, token, API-key, or mapping data.

#### Scenario: Installation without credentials

- **WHEN** a developer runs the locked synchronization and test commands without
  provider credentials or a configured vault
- **THEN** dependency setup succeeds or reports only dependency/configuration
  errors, without contacting or mutating any provider
