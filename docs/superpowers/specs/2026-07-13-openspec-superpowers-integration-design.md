# OpenSpec and Superpowers Integration Design

## Context

The repository currently keeps design specifications and implementation plans
under `docs/superpowers/`. Those documents are useful historical records, but
there is no initialized OpenSpec store and no structured lifecycle for active
changes.

The immediate active design is
`docs/superpowers/specs/2026-07-04-one-day-sync-cycling-design.md`. During this
design discussion its scope was updated from synchronizing exactly one Garmin
activity to synchronizing every activity for the requested date. The Weight x
Reps representation was also refined from a marker-only cycling row to the
documented structured time/distance set fields.

OpenSpec 1.5.0 is installed locally. Codex currently provides Superpowers
6.1.1, and OpenCode 1.16.2 is installed with an existing Warp plugin. The
community `superpowers-bridge` schema connects OpenSpec artifacts to the
Superpowers brainstorming, planning, worktree, TDD, subagent, review, and
branch-finishing workflows. It is listed in OpenSpec's community schema
catalog, but its published compatibility baseline is older than the local
versions and its validation is primarily structural rather than end-to-end.

## Goals

- Initialize OpenSpec for Codex and OpenCode.
- Keep `openspec/` as the versioned source of truth for new active work.
- Preserve existing `docs/superpowers/` files as project history.
- Migrate only the active one-day synchronization design into an OpenSpec
  change.
- Keep the built-in `spec-driven` schema as the stable project default.
- Pilot the community `superpowers-bridge` schema on the migrated change.
- Install the same pinned Superpowers release for OpenCode that Codex uses.
- Produce complete planning artifacts without implementing the synchronization
  feature or writing to Garmin, the Obsidian vault, or Weight x Reps.

## Non-Goals

- Migrating every historical Superpowers document.
- Making a community schema the default for every future change.
- Modifying the bridge to force compatibility if the unmodified pinned version
  fails validation or execution.
- Implementing `training-sync sync DATE` as part of the OpenSpec bootstrap.
- Performing live synchronization or authentication against external systems.
- Committing the pre-existing README edit as part of this work.

## Decisions

### 1. Adopt OpenSpec additively

The repository will use a hybrid transition:

- Existing `docs/superpowers/specs/` and `docs/superpowers/plans/` remain as
  historical records.
- New active work starts under `openspec/changes/`.
- Stable capability specifications live under `openspec/specs/` only after a
  completed change is verified, synchronized, and archived.

This avoids rewriting history while establishing an unambiguous source of
truth for future work.

### 2. Use a global custom OpenSpec workflow profile

The global OpenSpec profile will be changed from the implicit `core` default to
`custom`, with these workflows enabled:

- `propose`
- `explore`
- `new`
- `continue`
- `ff`
- `apply`
- `sync`
- `verify`
- `archive`

The expanded set is required to operate artifact-by-artifact schemas such as
`superpowers-bridge`. `bulk-archive` and `onboard` are excluded because they are
not needed for the current workflow. Delivery remains `both`, so supported
tools receive both skills and slash-command adapters.

The profile is global and therefore affects future `openspec init` or
`openspec update` operations. The previous global configuration must be
captured before it is changed so it can be restored precisely.

### 3. Generate local adapters for Codex and OpenCode

OpenSpec will be initialized with Codex and OpenCode adapters. The generated
`.codex/` and `.opencode/` project directories are local, regenerable adapter
output and will be ignored by Git. The `openspec/` directory is project state
and will be versioned.

This project-local `.opencode/` directory is separate from the user's global
`~/.config/opencode/opencode.json` configuration.

### 4. Pin Superpowers for OpenCode

The existing OpenCode plugin entry `@warp-dot-dev/opencode-warp` will be
preserved. The global plugin list will additionally contain:

```text
superpowers@git+https://github.com/obra/superpowers.git#v6.1.1
```

The `v6.1.1` tag exists upstream and matches the Superpowers version currently
provided to Codex. Pinning prevents an unrelated upstream update from changing
the workflow between tools.

### 5. Keep `spec-driven` as the default and vendor the bridge

`openspec/config.yaml` will keep `schema: spec-driven`. The project will vendor
the unmodified `superpowers-bridge` schema under
`openspec/schemas/superpowers-bridge/`, copied from upstream commit
`f5d40404856ad0f4ce9eb482cbb0e28cf434411f`.

The exact origin commit will be recorded beside the schema. The pilot change
will select `superpowers-bridge` through its change-local `.openspec.yaml`.
Other changes continue to use `spec-driven` unless explicitly opted in.

No local compatibility edits will be made during installation. If the pinned
schema does not validate or cannot drive the required artifact flow with
OpenSpec 1.5.0 and Superpowers 6.1.1, the pilot will fall back to
`spec-driven`.

### 6. Migrate one active change

The active work will become:

```text
openspec/changes/add-one-day-multi-activity-sync/
  .openspec.yaml
  brainstorm.md
  proposal.md
  design.md
  specs/
    daily-multi-activity-sync/spec.md
    weightxreps-cardio-sync/spec.md
  tasks.md
  plan.md
```

The bridge artifact graph is:

```text
brainstorm -> proposal -> specs -> tasks -> plan
          \-> design -----/
```

`verify.md` and `retrospective.md` are post-implementation artifacts and will
not be created during this bootstrap. The legacy active design will retain its
content and gain a short migration notice pointing to the OpenSpec change.

Planning artifacts will be committed before a future apply phase. This avoids
the bridge's known worktree hazard where untracked change artifacts may not be
visible inside a newly created implementation worktree.

### 7. Split the feature contract into two capabilities

`daily-multi-activity-sync` owns Garmin selection and daily-note behavior:

- Fetch every completed Garmin activity for the requested date.
- Fail before writing when no activity exists.
- Require the daily note to exist.
- Render all activities in stable order inside one `## 🏃 Training` section.
- Require `--yes` before replacing a non-empty training section.

`weightxreps-cardio-sync` owns the structured Weight x Reps conversion and
reconciliation:

- Preserve both strength and all cardiovascular activities when rebuilding the
  complete remote day.
- Resolve known exercises and stop on unknown or ambiguous mappings rather
  than silently creating exercises.
- Use set `type: 2` with actual distance and duration for running or cycling
  activities that have distance.
- Use set `type: 1` with actual duration for cardio without distance.
- Store Garmin metadata without native Weight x Reps fields in comment `c`,
  including activity name, heart rate, elevation, power, calories, and training
  load when present.
- Verify exercise, set type, duration, distance, and distance unit by reading
  the saved day back.

A single `--yes` authorizes both destructive replacements when the daily
section or remote day already contains data.

### 8. Preflight before writes and do not roll back the daily on remote failure

The future implementation will first collect and validate all Garmin
activities, the existing daily path, credentials, mappings, and the complete
Weight x Reps payload. Only then may it perform writes.

The daily is updated before Weight x Reps, matching the existing architecture
where the daily representation is the input to the Weight x Reps conversion.
If the remote write or read-back verification fails, the updated daily is not
rolled back. A remote timeout or verification mismatch can leave the remote
outcome uncertain; rolling back the local source would create a second
inconsistency. The command must instead fail clearly, show expected versus
observed state, and support an idempotent retry.

### 9. Record project-specific OpenSpec context

`openspec/config.yaml` will document:

- Python 3.10+, setuptools, and the `training-sync` console command.
- `python -m pytest` as the test entry point.
- Garmin as the source of completed activities.
- The existing Obsidian daily as the intermediate representation.
- Weight x Reps as a reconciled full-day destination with read-back
  verification.
- Project policies: test-driven implementation, no missing daily creation, no
  silent exercise creation, and no success report before read-back passes.

## Validation Strategy

The bootstrap is complete only when all of the following are true:

1. OpenSpec resolves and structurally validates the vendored
   `superpowers-bridge` schema.
2. `openspec validate --all --strict --no-interactive` succeeds.
3. The pilot change is complete through `plan.md`, while `verify.md` and
   `retrospective.md` remain correctly deferred.
4. Codex and OpenCode adapter directories exist and Git reports them as
   ignored.
5. OpenCode loads both the Warp and pinned Superpowers plugins, and the bridge's
   required Superpowers skills are discoverable.
6. The existing Python test suite still passes.
7. Git diffs and commits exclude the pre-existing README edit.

No live Garmin, Obsidian, or Weight x Reps writes are part of validation.

## Risks and Mitigations

- **Community schema version drift** -> Pin the exact upstream commit, validate
  it unchanged, keep `spec-driven` as the default, and fall back instead of
  patching opportunistically.
- **Global OpenSpec behavior changes for other repositories** -> Record the
  prior global configuration and limit the custom profile to the explicitly
  approved workflow set.
- **OpenCode plugin regression** -> Preserve the current plugin array, pin
  Superpowers to `v6.1.1`, validate the merged configuration, and retain the
  previous file content for rollback.
- **Generated adapter noise in Git** -> Ignore only `.codex/` and `.opencode/`;
  keep all OpenSpec source artifacts versioned.
- **Bridge worktree loses untracked artifacts** -> Commit planning artifacts
  before starting a future apply phase.
- **Duplicate or diverging specifications** -> Mark the one active legacy spec
  as migrated and treat the OpenSpec change as authoritative; leave unrelated
  historical documents untouched.
- **Partial external synchronization** -> Preflight before writes, verify the
  remote read-back, keep the daily as recoverable source state, and report an
  actionable partial failure.

## Implementation and Commit Boundaries

The work will use three isolated Conventional Commits:

1. `docs(openspec): design superpowers integration`
2. `chore(openspec): initialize codex and opencode workflows`
3. `docs(openspec): migrate multi-activity sync change`

The first commit contains only this approved bootstrap design. The second
contains the repository-owned OpenSpec initialization, project configuration,
vendored schema, and ignore rules. The global OpenSpec and OpenCode settings
are applied and validated during the same implementation phase but cannot be
part of a repository commit. The third commit contains the new change
artifacts and the migration notice on the legacy active design. The
pre-existing README modification remains outside these commits.

## Rollback

If the bootstrap must be reverted:

1. Restore the captured OpenSpec global profile and workflow settings.
2. Remove only the added Superpowers entry from OpenCode's global plugin list,
   preserving Warp and any subsequent user entries.
3. Remove the generated local adapters and the versioned OpenSpec bootstrap
   changes through their isolated commit.
4. Remove the migration notice from the legacy design if the OpenSpec pilot is
   abandoned.

If only the bridge fails, retain the OpenSpec initialization, remove the
change-local bridge selection, recreate the pilot artifacts using
`spec-driven`, and keep the rest of the setup intact.

## References

- OpenSpec community schemas catalog:
  <https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md#community-schemas>
- Community schema source:
  <https://github.com/JiangWay/openspec-schemas/tree/main/superpowers-bridge>
- OpenCode Superpowers installation:
  <https://github.com/obra/superpowers/blob/main/.opencode/INSTALL.md>
- Weight x Reps JEditor row format:
  <https://github.com/bandinopla/weightxreps-server/blob/main/docs/JEditorSaveRow.md>
- Weight x Reps set types:
  <https://github.com/bandinopla/weightxreps-client/blob/main/src/data/set-types.js>
