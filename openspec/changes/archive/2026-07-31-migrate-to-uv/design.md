## Context

The project already has valid PEP 621 metadata and a setuptools build backend,
so uv can operate on the existing `pyproject.toml` without changing the
package entry point or runtime dependency semantics. The current README is the
only installation guide, and the repository has no CI workflow to update.

## Goals / Non-Goals

**Goals:**

- Make fresh setup reproducible with a committed `uv.lock`.
- Make development and test dependencies explicit.
- Provide copyable commands for install, CLI execution, testing, lock updates,
  and locked verification.
- Retain Python 3.10+ compatibility and all local/provider safety boundaries.

**Non-Goals:**

- Changing runtime Python modules, provider APIs, credentials, or local config.
- Pinning the project to one personal Python installation or machine path.
- Removing standard package metadata or making pip installation technically
  impossible; uv becomes the documented project workflow.
- Adding CI when no CI workflow exists today.

## Decisions

### D1: Keep PEP 621 metadata and add a standard dev dependency group

- **Choice**: Retain `[project].dependencies` for runtime packages and add
  `pytest` under the standardized `[dependency-groups].dev` table.
- **Reason**: Runtime consumers and the setuptools build remain compatible,
  while uv gets an explicit development environment.
- **Alternative considered**: Put pytest in runtime dependencies; rejected
  because tests are not required by installed consumers.

### D2: Commit uv's lockfile

- **Choice**: Generate and commit `uv.lock` from the project metadata; use
  `uv sync --locked` for verification and fresh setup checks.
- **Reason**: A lockfile captures the resolved graph across machines while
  allowing the declared Python floor and markers to remain authoritative.
- **Alternative considered**: A generated requirements file; rejected because
  it duplicates metadata and is not the requested uv project workflow.

### D3: Use uv commands as the documented interface

- **Choice**: Document `uv sync --dev`, `uv run training-sync ...`,
  `uv run pytest -q`, `uv lock`, and `uv sync --locked`.
- **Reason**: These commands consistently use the project environment and make
  lock drift visible.
- **Alternative considered**: `uv run --with` ad hoc commands; rejected because
  they do not establish a reproducible project environment.

### D4: Preserve local configuration and provider boundaries

- **Choice**: Keep tokens, API keys, IDs, mappings, and vault paths under the
  existing local configuration convention; do not place values in metadata or
  `uv.lock`.
- **Reason**: Dependency tooling must not become a credential or provider
  configuration channel.
- **Alternative considered**: Add provider setup to `uv sync`; rejected because
  dependency installation must remain provider-isolated and side-effect free.

## Risks / Trade-offs

- [Risk] uv may not be installed on a new machine → Mitigation: README names
  uv as a prerequisite and gives its official installation entry point without
  storing machine-specific setup.
- [Risk] A lockfile can become stale after dependency edits → Mitigation:
  require `uv lock` for intentional updates and `uv sync --locked` in the
  verification workflow.
- [Trade-off] No CI workflow is added in this change → Accepted because none
  exists to migrate; the documented locked commands are CI-ready.

## Migration Plan

1. Add the dev dependency group and generate `uv.lock` without changing runtime
   dependencies or Python floor.
2. Verify the lock with `uv sync --locked`, run tests through `uv run`, and
   confirm the CLI entry point resolves.
3. Replace the primary README pip/venv examples with uv commands while keeping
   local configuration and authentication sections unchanged.
4. Rollback is deleting the uv-only metadata/docs changes; no runtime data or
   provider state is touched.

## Open Questions

None required before implementation. The explicit scope decision is to migrate
the project workflow and not add CI or modify provider integrations.
