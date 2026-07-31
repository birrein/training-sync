# Retrospective: direct-cli-install

> Written: 2026-07-31 (after verification passed)
> Commit range: no prior implementation commit; final documentation commit pending
> Worktree: current Training Sync checkout on `main`

## 0. Evidence

- **Implementation**: current-cycle README changes plus OpenSpec artifacts; no
  runtime code, lockfile, credentials, or provider integration changed.
- **Tasks done before delivery**: 9/9 tasks are marked complete; the final
  commit is the remaining delivery action after staging.
- **OpenSpec validation**: strict validation passed 9/9 before archive.
- **Test signal**: `uv run pytest -q` passed 270 tests in 0.51 seconds.
- **uv behavior signal**: isolated non-editable installation ran directly from
  `/tmp`; editable installation exposed a checkout-specific `.pth`; `--force`
  reinstalled; `uv tool upgrade` retained the original local source.
- **External/provider activity**: none. No real persistent tool installation,
  shell modification, credentials, or provider command was used.
- **Archive evidence**: the delta was archived and the stable
  `direct-cli-install` spec was validated as synchronized before staging.

## 1. Wins

- The operational UX now uses the direct `training-sync ...` command after a
  one-time persistent uv tool installation.
- The README clearly separates the operational tool environment from the
  repository's lock-backed `uv sync --locked --dev` and `uv run` workflow.
- The non-editable recommendation is evidence-backed: the launcher works from
  outside the checkout and does not bind operations to one source tree.
- Update semantics are explicit: `--force` selects a chosen local checkout,
  while `--editable` is documented as checkout-bound rather than portable.
- The change adds no personal paths, provider setup, credentials, CI, or global
  installation side effects.

## 2. Misses and corrections

- The preceding uv migration optimized for reproducible development commands
  but did not satisfy direct operational invocation. This follow-up keeps both
  use cases instead of conflating them.
- A simple `uv tool upgrade training-sync` would not be a reliable way to
  switch to an arbitrary checkout. The documentation now directs users to
  `uv tool install --force <checkout>` for that case.
- No runtime tests were added because the change is documentation and tool
  workflow only; isolated uv behavior plus the complete existing suite cover
  the changed contract.

## 3. Plan deviations

| Planned item | Actual result | Reason |
|---|---|---|
| Persistent user install | Not executed | The user requested documentation and explicitly prohibited unrequested global installation. |
| Editable install as default | Rejected | Isolated evidence showed the generated `.pth` points to one exact checkout. |
| Lockfile update | Not made | The operational tool environment is separate from the existing project lock. |

## 4. Skill / workflow compliance

| Skill | Used |
|---|---|
| `superpowers:brainstorming` | ✓ — approaches and trade-offs were evaluated before documentation edits. |
| `superpowers:writing-plans` | ✓ — the OpenSpec plan records exact behavior checks, documentation tasks, and delivery gates. |
| `openspec-verify-change` | N/A — unavailable; manual verification evidence is recorded above. |

No provider, credential, or external-service workflow was invoked.

## 5. Promote candidates

- [ ] **Distinguish an operationally installed CLI from a lock-backed project
  environment.** → **Promote to project guidance**
  > A reproducible development runner and a persistent user-facing executable
  > solve different lifecycle problems and should be documented separately.
- [ ] **Use source-directed reinstall semantics for local checkouts.** →
  **Promote to project tooling guidance**
  > When a package is not published, `uv tool install --force <checkout>` is
  > clearer and safer than implying a generic upgrade selects another tree.
