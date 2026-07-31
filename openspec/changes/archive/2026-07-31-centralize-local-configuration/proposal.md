## Why

Training Sync now has a working local vault configuration, but the convention
was introduced in code and README without an OpenSpec contract. A small
retrospective change makes the storage location, precedence, validation, and
separation of secrets from ordinary local values auditable for future settings.

## What Changes

- Record the already-integrated local configuration convention as a stable
  capability.
- Specify environment-over-file precedence for non-empty overrides.
- Specify required vault absence/invalid-path behavior and the no-personal-path
  versioning rule.
- Capture current implementation and test evidence without inventing a prior
  OpenSpec cycle.

## Capabilities

### New Capabilities

- `local-configuration`: Centralized local storage and precedence rules for
  machine-specific Training Sync configuration.

### Modified Capabilities

None.

## Impact

This is documentation and specification only. It adds a delta spec, then
archives it into `openspec/specs/local-configuration/spec.md`. The existing
implementation evidence is `789b6fe`; no provider, credential, or runtime code
is changed by this retrospective.
