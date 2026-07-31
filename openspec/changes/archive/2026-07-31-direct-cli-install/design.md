# Design: direct-cli-install

## Decision 1: Non-editable uv tool installation is the operational default

Use the project checkout as the source for a persistent isolated tool:

```bash
uv tool install /path/to/training-sync
uv tool update-shell
```

The first command installs the package into uv's tool environment and creates
the `training-sync` executable in uv's tool bin directory. The second command
helps add that directory to the user's PATH. The repository documentation will
tell the user to run the PATH helper if the executable directory is not already
on PATH; this change will not run it on the user's machine.

The non-editable installation copies/builds the package into the isolated tool
environment, so the command can run from another working directory or another
checkout. It is intentionally separate from the repository's `uv.lock`: the
lockfile governs project development and testing, while the tool environment is
the operational CLI installation.

## Decision 2: Editable installs are an explicit alternative, not the default

`uv tool install --editable /path/to/training-sync` reflects source changes
without reinstalling, but its generated editable path points to that exact
checkout. It is useful for developing the CLI locally, but it is not portable
across checkouts and must not be documented as the normal operational install.

## Decision 3: Updates are source-directed and explicit

When a different checkout or a newer local commit should supply the direct
command, run:

```bash
uv tool install --force /path/to/training-sync
```

`--force` recreates the existing tool environment and replaces the executable.
`uv tool upgrade training-sync` can refresh the originally recorded tool source,
but it does not select an arbitrary new checkout; the documentation will prefer
the explicit `--force` command for local source updates.

## Decision 4: Keep development and operation visibly separate

Operational examples use:

```bash
training-sync sync YYYY-MM-DD
```

Development and test examples continue to use:

```bash
uv sync --locked --dev
uv run pytest -q
uv run training-sync --help
```

No provider command is executed during installation, and no credentials,
vault path, mappings, or IDs are part of the tool installation instructions.

## Rejected alternatives

- `uv run training-sync ...` as the only operational form: reproducible for
  development, but does not satisfy the direct command UX.
- `uv tool install --editable .` as the default: source changes are convenient,
  but the executable retains a checkout-specific editable path.
- A machine-specific shell script or hardcoded absolute checkout path: not
  portable and outside repository scope.
- Installing the tool globally during this change: explicitly not authorized;
  only isolated temporary validation is performed.
