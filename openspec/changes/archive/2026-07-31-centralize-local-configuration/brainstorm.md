# Retrospective design capture: centralize-local-configuration

This is a retrospective record, not a pre-implementation design session. The
implementation was already integrated in `789b6fe` before this OpenSpec change
was created.

## Observed problem

The vault root was initially hardcoded to one user's machine. The correction
needed an explicit per-machine configuration without committing personal paths,
while preserving the project's existing `~/.config/training-sync/` convention.

## Recorded decisions

1. Keep persistent machine-specific values under `~/.config/training-sync/`.
2. Give a non-empty environment variable priority over the matching local file.
3. Store the vault root in `vault-root` and require an absolute path.
4. Fail required vault-backed commands before loading provider tokens or clients.
5. Keep credentials/secrets separate from IDs, mappings, and filesystem paths.

## Evidence boundary

The code and tests for the vault behavior are in `789b6fe`; the merge that put
that implementation on `main` is `e7f477a`. This change records and stabilizes
that contract; it does not claim a new implementation cycle.
