# Retrospective: centralize-local-configuration

> Written: 2026-07-31 (after verify passed)
> Commit range: `789b6fe` implementation evidence; no prior implementation
> commits belong to this retrospective cycle
> Worktree: `/Users/birrein/.codex/worktrees/b1cb/training-sync` on `main`

---

## 0. Evidence

- **Implementation evidence**: `789b6fe feat(config): centralize local vault configuration` (+166 / -15 lines across 5 runtime/test/docs files), integrated by `e7f477a`.
- **Retrospective artifacts**: 8 authored OpenSpec artifacts plus generated metadata/README, all created under `openspec/changes/centralize-local-configuration/`.
- **Tasks done**: 5/5 (`grep -cE '^\s*- \[x\]' tasks.md` → 5; unchecked → 0).
- **Active hours**: n/a — cold retrospective backfill; evidence was reconstructed from Git, current files, and tests.
- **Subagent dispatches**: n/a — no runtime implementation was performed in this cycle.
- **New external dependencies**: none.
- **Bugs encountered post-merge**: none observed in the current test run.
- **OpenSpec validate state at archive**: strict validation passed before archive (7/7 items valid).
- **Test coverage signal**: `PYTHONPATH=src pytest -q` → 270 passed in 0.41s.

Commit chain relevant to this record:

```text
789b6fe feat(config): centralize local vault configuration
e7f477a merge(feature): integrate canonical activity reconciliation
```

The feature merge is included as integration context only; this retrospective
does not claim that canonical activity work was part of the configuration change.

## 1. Wins

- [evidence: `789b6fe`, `src/training_sync/config.py`] The vault moved from a
  personal hardcoded default to `vault-root` under the central local directory,
  with a shared environment-over-file loader.
- [evidence: `789b6fe`, `tests/test_config.py`] Precedence, local-file fallback,
  absence, and relative-path rejection are represented by focused tests.
- [evidence: `789b6fe`, `src/training_sync/cli.py`, `tests/test_training_sync_cli.py`]
  Vault validation occurs before token loading and provider client construction.
- [evidence: `openspec validate --all --strict --json`, `verify.md`] The
  retrospective contract is structurally valid before archive and aligns its
  four requirements with the design decisions.

## 2. Misses

- 🟡 [painful | evidence: parent of `789b6fe`] The original implementation was
  integrated before an OpenSpec capability captured its contract, requiring a
  cold retrospective rather than a change-first cycle.
- 🟡 [painful | evidence: `src/training_sync/config.py:60-69` on current main]
  The existing Intervals API-key loader has its own local-file precedence code;
  this record classifies it as a secret but does not falsely claim it was
  refactored by `789b6fe`.
- 📌 [nit | evidence: `verify.md` §6] Historical `docs/superpowers/specs/`
  files remain in the repository; no new artifact from this cycle leaked there.

## 3. Plan deviations

| Plan task | What changed | Why |
|---|---|---|
| Task 1 | Reconstructed evidence from merged `main` instead of an implementation worktree | The runtime change was already merged before this OpenSpec cycle began. |
| Task 2 | Used the documented manual verification checklist instead of `openspec-verify-change` | That skill was not available in the session; the required seven checks were run and recorded in `verify.md`. |
| Task 2 | No runtime implementation task or commit was created | The user requested retrospective documentation and explicitly required an honest record of existing work. |

## 4. Skill / workflow compliance

| Skill | Used |
|---|---|
| `superpowers:brainstorming` | N/A — retrospective evidence capture, not a new design session |
| `superpowers:writing-plans` | N/A — plan records completed documentation steps; no runtime plan execution |
| `superpowers:using-git-worktrees` | N/A — this cycle was authorized on the existing clean `main` worktree |
| `superpowers:subagent-driven-development` | N/A — no implementation task was delegated |
| (transitive) `superpowers:test-driven-development` | N/A — implementation and tests predate this retrospective |
| (transitive) `superpowers:requesting-code-review` | N/A — no new code was produced |
| `openspec-verify-change` | N/A — unavailable; manual seven-check fallback recorded in `verify.md` |
| `superpowers:finishing-a-development-branch` | N/A — this documentation cycle is completed on `main`, not a feature branch |

### Deliberately Skipped Skills

- **Runtime implementation skills listed above**
  - **What was skipped**: Their apply-phase execution was not invoked.
  - **Why this cycle**: `789b6fe` already contains the runtime implementation,
    and every task in this change is an evidence/spec/archive task; invoking an
    implementation workflow would misrepresent the history.
  - **How to prevent recurrence**: `scope-judgment rule` — create OpenSpec
    before implementation for future runtime changes; use retrospective
    backfills only when the implementation commit is explicitly cited.

- **`openspec-verify-change`**
  - **What was skipped**: The skill invocation itself; the seven checks were
    performed manually.
  - **Why this cycle**: The skill was absent from the available skills list.
  - **How to prevent recurrence**: `schema boundary case, no prevention
    possible` — use the schema's manual fallback whenever the skill is not
    installed, and record the exact command outputs in `verify.md`.

## 5. Surprises

- The merged feature branch introduced a separate `intervals-api-key` loader,
  so the local configuration convention is documented as an explicit contract
  for future adoption rather than retroactively claiming all loaders share the
  helper.
- The implementation needed both a persistent local file and an optional
  environment override; either source alone would not satisfy the multi-machine
  and no-personal-default requirements.

## 6. Promote candidates → long-term learning

- [ ] 🟡 **Every new local setting should declare its env name, local filename,
  precedence, validation, and absence behavior together.** → **Promote to
  project configuration guidance**
  > **Why**: The vault contract was implemented before its OpenSpec contract,
  > while a later API-key loader used separate precedence code.
  > **How to apply**: Before adding a setting, update `training_sync.config`,
  > focused tests, the stable spec, and README in the same change.
