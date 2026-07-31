# Design exploration: migrate-to-uv

## Current context

`main` is clean at `0cafe77` and already contains the local configuration
contract. The project uses setuptools metadata in `pyproject.toml`, declares
Python `>=3.10`, documents `python3 -m venv` plus `pip install -e .`, and has no
`.github` CI workflow. There is no `uv.lock` or development dependency group.

## Approaches considered

### A. Adopt uv project workflow with a checked-in lockfile (recommended)

Keep the existing PEP 621 metadata and runtime dependencies, add a standard
development dependency group for pytest, generate `uv.lock`, and document
`uv sync`, `uv run`, and `uv sync --locked`. This gives each machine the same
resolved dependency graph without changing provider behavior.

### B. Keep pip metadata and generate a requirements lock

Add a generated requirements file while retaining venv/pip instructions. This
would duplicate dependency sources and leave the requested workflow split
between two tools.

### C. Use uv only as an ephemeral runner

Document `uv run --with ...` commands without a project lockfile. This avoids
metadata edits but cannot provide a reproducible project environment or a
clear place for development-only dependencies.

## Recorded recommendation

Choose A. Preserve `requires-python = ">=3.10"` and the existing runtime
dependencies, add `pytest` to the standard dev dependency group, check in
`uv.lock`, and make `uv sync --locked` the reproducibility gate. Keep local
tokens, API keys, mappings, and vault paths in `~/.config/training-sync/`; no
credential or provider configuration belongs in `pyproject.toml` or the lock.

No CI workflow will be invented because this repository currently has none.
The migration will document local development/test commands and a future CI
consumer can use the same locked commands.
