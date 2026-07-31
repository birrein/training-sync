## Why

Training Sync is now intended for use on multiple machines, but its documented
setup still requires each user to create a venv and install from pip without a
committed resolution. That makes fresh environments less reproducible and
leaves development dependencies implicit. uv can provide one locked project
workflow while retaining the package's Python 3.10+ compatibility and local
provider configuration boundaries.

## What Changes

- Add a checked-in `uv.lock` generated from the existing project metadata.
- Declare development-only test dependencies in `pyproject.toml` using a
  standard dependency group.
- Replace primary README setup/test examples with `uv sync`, `uv run`, and
  `uv sync --locked` commands.
- Preserve runtime dependency names, Python `>=3.10`, credentials, local
  configuration, and provider behavior.

## Capabilities

### New Capabilities

- `uv-development-workflow`: Reproducible installation, development, and test
  commands for the Python project using uv and its lockfile.

### Modified Capabilities

None.

## Impact

The implementation will affect `pyproject.toml`, add `uv.lock`, and update
README installation and development instructions. It will not change Python
runtime code, provider clients, credentials, local configuration files, or
external integrations. No CI workflow currently exists, so CI creation is out
of scope for this change.
