# direct-cli-install Specification

## Purpose
Define the portable direct operational CLI installation and its separation from
the repository's lock-backed uv development and testing workflow.
## Requirements
### Requirement: Provide a persistent direct operational command

The README MUST document a non-editable `uv tool install` command that installs
the local project as an isolated tool and makes the `training-sync` executable
available independently of the current working directory. The instructions
MUST include the uv tool executable directory PATH helper without executing a
machine-global installation as part of the project change.

#### Scenario: Direct command from another working directory

- **WHEN** a developer installs a checkout with `uv tool install` and has uv's
  tool executable directory on PATH
- **THEN** `training-sync --help` and operational `training-sync ...` commands
  run directly from outside that checkout

### Requirement: Distinguish editable and source-update semantics

The README MUST state that `uv tool install --editable` binds the operational
tool to the selected checkout, and MUST document
`uv tool install --force <checkout>` as the explicit way to reinstall from a
chosen local checkout. The documentation MUST NOT imply that `uv tool upgrade`
selects an arbitrary different checkout.

#### Scenario: A different checkout becomes operational source

- **WHEN** a developer wants the direct command to use another local checkout
- **THEN** they run `uv tool install --force <checkout>` and the tool environment
  and executable are replaced from that selected source

#### Scenario: Editable install is evaluated

- **WHEN** a developer chooses `uv tool install --editable <checkout>`
- **THEN** the documentation warns that source changes are reflected from that
  exact checkout and that the form is not the portable multi-checkout default

### Requirement: Keep development and operational workflows separate

The README MUST use direct `training-sync ...` commands for operational
examples, while retaining `uv sync --locked --dev`, `uv run pytest -q`, and
`uv run training-sync --help` for project development and test validation. The
direct tool installation MUST NOT change or replace the committed `uv.lock`.

#### Scenario: Development remains lock-backed

- **WHEN** a developer prepares the project with `uv sync --locked --dev`
- **THEN** tests and development commands run through `uv run` using the
  repository's locked environment, independently of the persistent tool

### Requirement: Preserve local and provider boundaries

The direct-install instructions MUST use neutral paths and MUST NOT require,
read, write, version, or alter credentials, vault paths, IDs, mappings, or
provider state. No provider command or persistent tool installation may run as
an automatic side effect of the documented project change.

#### Scenario: Installation without local configuration

- **WHEN** a developer follows the direct-install instructions without provider
  credentials or a configured vault
- **THEN** uv installs the CLI package without contacting or mutating Garmin,
  Weight x Reps, Intervals.icu, or the vault
