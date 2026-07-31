# Verification Report

**Change**: `direct-cli-install`
**Verified at**: `2026-07-31`
**Verifier**: Codex (manual verification; no dedicated OpenSpec verifier skill is available)

## 1. Structural validation

- [x] `openspec validate --all --strict --json` passed 9/9 items: the active
  change plus 8 stable specs, with 0 failures.

## 2. Task completion

- [x] Tasks 1.1–1.3: local uv help and isolated non-editable, editable, force
  reinstall, and upgrade behavior.
- [x] Tasks 2.1–2.3: direct operational documentation, development/testing
  distinction, editable limitation, and configuration boundary.
- [x] Task 3.1: strict validation, locked sync, full suite, CLI smoke test, and
  diff check.
- [x] Tasks 3.2–3.3: retrospective/archive and final commit scope prepared;
  the actual commit remains the final delivery action after staging.

## 3. uv behavior evidence

- uv version: `0.11.19`.
- `uv tool install --help` confirms `--editable` and `--force`; help states that
  tools use isolated virtual environments and that executables are linked into
  the uv tool bin directory.
- `uv tool dir --bin` identifies the executable directory and
  `uv tool update-shell --help` confirms the PATH helper.
- In isolated temporary `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` directories,
  `uv tool install <checkout>` installed `training-sync` and its launcher.
- With the temporary bin directory prepended to PATH, `training-sync --help`
  exited 0 from `/tmp`, outside the checkout.
- `uv tool install --force <checkout>` recreated the isolated environment and
  replaced the executable successfully.
- `uv tool install --editable <checkout>` created an editable `.pth` pointing
  at that exact checkout's `src` directory, confirming the documented
  multi-checkout limitation.
- `uv tool upgrade training-sync` refreshed the recorded local source and
  reported no upgrade; it did not select an arbitrary different checkout.
- No persistent tool was installed in the user's real uv tool directory, and
  `uv tool update-shell` was not executed against the user's shell.

## 4. Validation evidence

```text
openspec validate --all --strict --json
items: 9, passed: 9, failed: 0

uv lock --check
exit 0

uv sync --locked --dev
exit 0

uv run pytest -q
270 passed in 0.51s

uv run training-sync --help
exit 0

git diff --check
exit 0
```

Additional checks found no operational examples prefixed with `uv run`, and no
personal path matches in README, code, tests, project metadata, lockfile, or
the active OpenSpec artifacts.

## 5. Scope and safety

- [x] Only README and OpenSpec artifacts are changed; no runtime code or
  `uv.lock` change is required.
- [x] No credentials, vault paths, mappings, IDs, or provider state were read or
  changed.
- [x] No provider command was run.
- [x] No persistent machine installation or shell modification was performed.
- [x] No CI or global project configuration was added.

## 6. Stable spec synchronization

- [x] `openspec archive -y direct-cli-install` completed successfully.
- [x] `openspec/specs/direct-cli-install/spec.md` contains the four archived
  requirements and five scenarios.
- [x] The stable spec purpose was replaced with a concrete description; no
  `TBD` purpose remains.

The normalized requirements in the archived delta and stable spec compare
identically.

## Overall decision

- [x] PASS WITH WARNINGS — implementation, archive, stable-spec synchronization,
  and validation pass; the single final commit remains the sequenced delivery
  action
- [ ] PASS — all delivery actions complete
- [ ] FAIL

**Next step**: write the retrospective, archive the change, compare its stable
spec, then stage and create the single Conventional Commit without pushing.
