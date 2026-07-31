# Migrate Training Sync to uv Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the documented pip/venv development path with a reproducible uv project workflow while preserving Python 3.10+ and local/provider boundaries.

**Architecture:** Keep PEP 621 runtime metadata in `pyproject.toml`, add a
standard dev dependency group for pytest, and commit the resolver output in
`uv.lock`. README commands use `uv sync` and `uv run`; no runtime Python module,
credential file, provider client, or CI workflow is changed.

**Tech Stack:** Python 3.10+, setuptools, uv, PEP 621 `pyproject.toml`,
`uv.lock`, pytest, and Markdown documentation.

## Global Constraints

- Preserve `requires-python = ">=3.10"` exactly.
- Keep Garmin, Weight x Reps, Intervals.icu, vault, tokens, API keys, and mappings outside dependency setup.
- Do not add personal paths, credentials, provider calls, or a CI workflow.
- Use `uv sync --locked` for reproducibility checks and `uv run pytest -q` for tests.
- Update `uv.lock` only through `uv lock` after intentional metadata changes.

---

### Task 1: Project metadata and lockfile

**Files:**
- Modify: `pyproject.toml`
- Create: `uv.lock`
- Test: `tests/` (existing suite; no new runtime test expected)

**Interfaces:**
- Consumes: existing `[project]` metadata, runtime dependencies, and Python floor.
- Produces: a uv project with a `dev` dependency group containing pytest and a committed lockfile.

- [ ] **Step 1: Record the pre-change dependency contract**

Run:

```bash
sed -n '1,120p' pyproject.toml
```

Expected: the existing runtime dependency names and `requires-python = ">=3.10"` are captured before editing.

- [ ] **Step 2: Add only the development dependency declaration**

Add:

```toml
[dependency-groups]
dev = ["pytest"]
```

Keep the existing `[project].dependencies` list unchanged.

- [ ] **Step 3: Generate the lockfile**

Run:

```bash
uv lock
```

Expected: `uv.lock` is created or updated, resolves the project for Python
3.10+, and contains dependency metadata only.

- [ ] **Step 4: Verify locked synchronization**

Run:

```bash
uv sync --locked --dev
```

Expected: the environment synchronizes without changing `uv.lock` and without
requiring credentials or contacting a provider.

- [x] **Step 5: Defer the metadata commit to the final migration commit**

The user requested one Conventional Commit covering this migration, so no
intermediate commit is created.

### Task 2: uv developer and test documentation

**Files:**
- Modify: `README.md:20-40` (installation) and the development/test guidance added by this change.

**Interfaces:**
- Consumes: `uv.lock` and the `dev` group from Task 1.
- Produces: copyable setup, CLI, test, lock-update, and lock-verification commands.

- [ ] **Step 1: Replace the primary setup path**

Document the uv prerequisite and:

```bash
uv sync --dev
```

Do not present `python -m venv`, `source venv/bin/activate`, or `pip install -e .`
as the primary workflow.

- [ ] **Step 2: Document project commands**

Add these exact patterns:

```bash
uv run training-sync --help
uv run training-sync sync YYYY-MM-DD
uv run pytest -q
uv lock
uv sync --locked --dev
```

Keep the existing local configuration, token, API-key, and provider-safety
instructions unchanged except for command prefixes where appropriate.

- [x] **Step 3: Defer the documentation commit to the final migration commit**

The README is committed together with the metadata and OpenSpec evidence after
final validation.

### Task 3: Final verification and safety review

**Files:**
- Inspect: `pyproject.toml`, `uv.lock`, `README.md`
- Inspect: `src/training_sync/config.py`, provider auth/client modules, and `git diff`

**Interfaces:**
- Consumes: completed Tasks 1-2.
- Produces: evidence that the migration is locked, runnable, and isolated from
  credentials/providers.

- [ ] **Step 1: Verify lock drift detection**

Run:

```bash
uv lock --check
uv sync --locked --dev
```

Expected: both commands exit 0 and do not rewrite the lockfile.

- [ ] **Step 2: Run the full test suite through uv**

Run:

```bash
uv run pytest -q
```

Expected: all existing tests pass using the uv-managed environment.

- [ ] **Step 3: Smoke-test the installed CLI without provider access**

Run:

```bash
uv run training-sync --help
```

Expected: help text exits 0 without reading credentials or contacting a
provider.

- [ ] **Step 4: Inspect scope and formatting**

Run:

```bash
git diff --check
rg -n "(token|api.key|vault|garmin|weightxreps|intervals)" uv.lock pyproject.toml
```

Expected: dependency files contain no secret values, personal paths, or
provider configuration; only intended package metadata/docs are changed.

- [x] **Step 5: Create the single final migration commit**

```bash
git status --short
git commit -m "build(uv): migrate development workflow"
```

Expected: only the intended uv migration files are committed; no credentials,
provider state, or unrelated worktree changes are present.
