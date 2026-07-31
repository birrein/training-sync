# Retrospective: migrate-to-uv

> Written: 2026-07-31 (after verification passed)
> Commit range: no prior implementation commit; final migration commit pending
> Worktree: current Training Sync checkout on `main`

## 0. Evidence

- **Implementation**: current-cycle changes to `pyproject.toml`, `README.md`,
  and generated `uv.lock`; no runtime module or provider integration changed.
- **OpenSpec artifacts**: proposal, design, plan, tasks, delta spec, verify,
  and this retrospective are under the active `migrate-to-uv` change.
- **Tasks done before delivery**: 7/7 tasks are marked complete; the single
  final commit is prepared as the delivery action after archive.
- **OpenSpec validation**: strict validation passed 8/8 before archive.
- **Test signal**: `uv run pytest -q` passed 270 tests in 0.68 seconds.
- **New dependency declarations**: `pytest` was added only to the standard
  development dependency group; runtime dependencies were not changed.
- **Provider activity**: none. No credentials, local configuration, or
  provider commands were used.

## 1. Wins

- The project now has a reproducible, versioned uv lockfile while retaining
  PEP 621 metadata, setuptools, and Python 3.10+ support.
- The README gives copyable setup, CLI, test, lock-refresh, and locked-sync
  commands through `uv run` and `uv sync`.
- The implementation keeps development-only pytest dependencies separate from
  runtime dependencies and does not add CI or provider setup.
- The explicit path scan found no personal vault paths or machine-specific
  names in the migration files, code, tests, metadata, or lockfile.
- The active delta was archived and the stable `uv-development-workflow` spec
  was validated as synchronized before staging.

## 2. Misses and corrections

- The initial design wording said installation should remain “offline”. That
  was corrected before archive to “provider-isolated”, because uv may contact a
  package index to resolve or install dependencies while still never touching
  Garmin, Weight x Reps, Intervals.icu, credentials, or vault state.
- No new runtime tests were necessary: this change affects project metadata,
  lock resolution, and documentation. The existing full suite plus uv lock and
  CLI smoke checks provide the relevant evidence.

## 3. Plan deviations

| Planned item | Actual result | Reason |
|---|---|---|
| Intermediate metadata commit | Not created | The user explicitly requested one Conventional Commit for the migration. |
| Intermediate documentation commit | Not created | README and metadata are staged together after final archive validation. |
| Final verification commit | Deferred to final delivery | OpenSpec verify/retrospective/archive and stable-spec comparison must precede the one commit. |
| CI workflow | Not added | No CI migration was requested and none existed in the repository. |

## 4. Skill / workflow compliance

| Skill | Used |
|---|---|
| `superpowers:brainstorming` | ✓ — design alternatives and constraints were recorded before implementation. |
| `superpowers:writing-plans` | ✓ — the active plan drove metadata, documentation, and validation tasks. |
| `superpowers:executing-plans` | ✓ — implementation followed the reviewed plan with validation gates. |
| `openspec-verify-change` | N/A — unavailable; the manual verification checklist is recorded in `verify.md`. |

No provider, credential, or external-service workflow was invoked.

## 5. Promote candidates

- [ ] **Keep dependency workflow and provider configuration explicitly
  separate.** → **Promote to project guidance**
  > New project tooling should document what it owns and prove that local
  > credentials, mappings, IDs, vault paths, and provider clients remain out of
  > its setup path.
- [ ] **Prefer one final migration commit when the user requests a bounded
  > commit scope.** → **Promote to delivery guidance**
  > It keeps metadata, lockfile, docs, and OpenSpec evidence auditable as one
  > change while avoiding intermediate history that the user did not request.
