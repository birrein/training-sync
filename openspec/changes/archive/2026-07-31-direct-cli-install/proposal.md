# Proposal: direct-cli-install

## Why

The uv migration made `uv run training-sync ...` the primary command form, but
operational use requires the installed `training-sync` command to be callable
directly with flags from any working directory. The project needs a persistent,
local CLI installation path without weakening the repository's locked
development workflow.

## What changes

- Document `uv tool install <checkout>` as the persistent non-editable CLI
  installation for operational use.
- Document `uv tool update-shell` as the one-time PATH helper, without running
  it automatically or adding a machine-global installation in this change.
- Document that `--editable` binds the tool to one checkout and is not the
  portable recommendation for multiple checkouts.
- Document `uv tool install --force <checkout>` as the explicit reinstall/update
  operation when a different checkout should become the operational source.
- Separate direct operational commands from `uv run` development and testing
  commands in the README.

## Scope

This is documentation and OpenSpec only. It does not change Python runtime
code, credentials, local configuration, provider integrations, CI, or the
project lockfile.
