# Direct CLI Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document a persistent direct `training-sync` command installed with uv while retaining `uv run` for development and tests.

**Architecture:** Keep the repository's `uv.lock` and project environment as the reproducible development boundary. Add a separate documented uv tool environment for operational CLI use, installed non-editably from a selected checkout and updated explicitly with `--force` when another checkout should become the source.

**Tech Stack:** Python 3.10+, setuptools, uv tool environments, `uv.lock`, Markdown, OpenSpec.

## Global Constraints

- Do not install a persistent tool on the user's machine during this change.
- Do not modify credentials, local configuration, vault paths, mappings, IDs, provider code, CI, or `uv.lock`.
- Use neutral paths such as `/path/to/training-sync`; never add personal checkout paths.
- Operational commands use direct `training-sync`; development and tests use `uv run`.
- The non-editable install is the recommendation for cross-checkout use; editable installs must document their checkout binding.
- Verify update/reinstall semantics with isolated `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` locations.

---

### Task 1: Record and validate uv tool behavior

**Files:**
- Inspect: `pyproject.toml`, `uv.lock`, `README.md`
- Test: isolated temporary uv tool directories outside the repository

**Interfaces:**
- Consumes: the existing console script `training-sync = "training_sync.cli:main"`.
- Produces: evidence for non-editable direct execution, editable checkout binding, PATH location, `--force` reinstall, and `uv tool upgrade` source behavior.

- [x] **Step 1: Inspect local uv help**

Run `uv tool install --help`, `uv tool upgrade --help`, `uv tool dir --help`,
and `uv tool update-shell --help`. Confirm the flags and PATH behavior used by
the design.

- [x] **Step 2: Validate non-editable direct execution in isolation**

Set `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` to temporary directories, run
`uv tool install <checkout>`, then invoke the generated `training-sync --help`
from `/tmp`. Confirm the launcher works outside the checkout.

- [x] **Step 3: Validate editable and update behavior in isolation**

Run `uv tool install --editable <checkout>`, inspect the generated editable
`.pth` path, run `uv tool install --force <checkout>`, and observe
`uv tool upgrade training-sync` without changing the user's real tool directory.

### Task 2: Update the operational documentation

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the behavior evidence and decisions in `design.md`.
- Produces: direct operational command examples and a separate development/test section.

- [x] **Step 1: Add persistent direct-install instructions**

Document `uv tool install /path/to/training-sync`, the PATH helper
`uv tool update-shell`, and the neutral `uv tool install --force
/path/to/training-sync` update form. State that this change does not execute the
installation automatically.

- [x] **Step 2: Separate command classes**

Change operational examples to direct `training-sync ...` invocations. Keep
`uv run pytest -q` and `uv run training-sync --help` in development/testing
guidance, and explain that `uv.lock` governs project development rather than
the separate operational tool environment.

- [x] **Step 3: Document editable limitation and local configuration boundary**

Explain that `--editable` points to one checkout and is not the portable
recommendation. Preserve the existing credentials, vault, mappings, IDs, and
provider safety instructions unchanged.

### Task 3: Validate, archive, and deliver the documentation change

**Files:**
- Inspect: all changed README/OpenSpec files and `git diff`

**Interfaces:**
- Consumes: completed documentation and isolated behavior evidence.
- Produces: strict OpenSpec validation, archived delta, stable spec, and one
  Conventional Commit on `main` with no push.

- [x] **Step 1: Run validation**

Run `openspec validate --all --strict --json`, `git diff --check`, and the
existing full suite through `uv run pytest -q`. Confirm no provider command or
credential access is involved.

- [x] **Step 2: Complete verify and retrospective**

Record exact isolated uv behavior, test output, scope review, and the
editable/source-update limitation in `verify.md` and `retrospective.md`.

- [x] **Step 3: Archive and compare the stable spec**

Run `openspec archive -y direct-cli-install`, validate again, and compare the
archived delta requirements with `openspec/specs/direct-cli-install/spec.md`.

- [x] **Step 4: Commit only this change**

Stage README and the archived/stable OpenSpec artifacts, run staged diff checks,
and create one Conventional Commit. Do not push or alter other branches.
