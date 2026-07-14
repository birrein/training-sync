# OpenSpec and Superpowers Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Initialize a versioned OpenSpec workflow for Codex and OpenCode, install a pinned Superpowers bridge as an optional schema, and migrate the active multi-activity synchronization design into a fully planned OpenSpec change without implementing it.

**Architecture:** OpenSpec remains project-local and uses built-in `spec-driven` by default. A byte-for-byte vendored `superpowers-bridge` schema is selected only by `add-one-day-multi-activity-sync`; generated Codex/OpenCode adapters stay local and ignored, while global workflow/plugin configuration is changed reversibly outside Git.

**Tech Stack:** OpenSpec 1.5.0, Node.js 22.20.0 via nvm, Superpowers 6.1.1, OpenCode 1.16.2, YAML/Markdown, Python 3.10+, pytest.

## Global Constraints

- Preserve the pre-existing `README.md` modification and never stage it in this work.
- Preserve all existing `docs/superpowers/` history; migrate only `2026-07-04-one-day-sync-cycling-design.md`.
- Keep `schema: spec-driven` as the project default.
- Vendor `superpowers-bridge` from exact commit `f5d40404856ad0f4ce9eb482cbb0e28cf434411f` without modifying upstream-owned files.
- Pin the OpenCode Superpowers plugin to exact tag `v6.1.1` and preserve `@warp-dot-dev/opencode-warp`.
- Enable exactly `propose`, `explore`, `new`, `continue`, `ff`, `apply`, `sync`, `verify`, and `archive`; keep delivery set to `both`.
- Ignore generated `.codex/` and `.opencode/` directories; version all `openspec/` source artifacts.
- Do not implement the synchronization feature or write to Garmin, Obsidian, or Weight x Reps.
- Run `python -m pytest -q`; the baseline is `97 passed`.

---

## File Map

- Modify `/Users/birrein/.config/openspec/config.json`: global custom profile and selected workflows; not committed.
- Modify `/Users/birrein/.config/opencode/opencode.json`: add pinned Superpowers plugin while retaining Warp; not committed.
- Modify `.gitignore`: ignore only generated Codex/OpenCode adapter roots.
- Create `openspec/config.yaml`: stable default schema, project context, and artifact rules.
- Create `openspec/schemas/superpowers-bridge/`: exact upstream schema package plus local provenance file.
- Generate `.codex/` and `.opencode/`: OpenSpec adapters; ignored and regenerable.
- Create `openspec/changes/add-one-day-multi-activity-sync/`: pilot change and all pre-implementation artifacts.
- Modify `docs/superpowers/specs/2026-07-04-one-day-sync-cycling-design.md`: add only a migration notice.
- Track `docs/superpowers/plans/2026-07-13-openspec-superpowers-integration.md`: this execution plan, included with the bootstrap commit.

### Task 1: Configure global OpenSpec and OpenCode integration

**Files:**
- Modify: `/Users/birrein/.config/openspec/config.json`
- Modify: `/Users/birrein/.config/opencode/opencode.json`

**Interfaces:**
- Consumes: OpenSpec's global `profile`, `delivery`, and `workflows` settings; OpenCode's `plugin` array.
- Produces: a custom OpenSpec workflow set and an OpenCode runtime exposing Superpowers 6.1.1 alongside Warp.

- [ ] **Step 1: Capture and verify the current global state**

Run:

```bash
openspec config list --json
sed -n '1,200p' "$HOME/.config/openspec/config.json"
sed -n '1,200p' "$HOME/.config/opencode/opencode.json"
```

Expected before mutation: resolved OpenSpec values include `"profile": "core"` and `"delivery": "both"`; the raw OpenSpec file has no explicit `profile`, `delivery`, or `workflows`; and OpenCode contains only `"@warp-dot-dev/opencode-warp"` in its plugin array. If either file changed since planning, preserve every unrelated key and recompute only the approved edits below.

- [ ] **Step 2: Set the exact non-interactive OpenSpec workflow profile**

Run the array update before activating `custom`, so there is no intermediate custom profile with zero workflows:

```bash
openspec config set workflows '["propose","explore","new","continue","ff","apply","sync","verify","archive"]'
openspec config set profile custom
```

Expected: both commands report success and preserve `delivery: both` plus telemetry fields. Rollback to the originally implicit defaults is:

```bash
openspec config unset profile
openspec config unset workflows
```

- [ ] **Step 3: Add pinned Superpowers to OpenCode without replacing Warp**

Use `apply_patch` on `/Users/birrein/.config/opencode/opencode.json` so its plugin array becomes exactly:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "@warp-dot-dev/opencode-warp",
    "superpowers@git+https://github.com/obra/superpowers.git#v6.1.1"
  ]
}
```

Do not add the Superpowers entry a second time if it is already present.

- [ ] **Step 4: Verify the global OpenSpec values structurally**

Run:

```bash
openspec config list --json | python -c 'import json,sys; c=json.load(sys.stdin); assert c["profile"] == "custom"; assert c["delivery"] == "both"; assert c["workflows"] == ["propose","explore","new","continue","ff","apply","sync","verify","archive"]'
```

Expected: exit code 0 with no assertion output.

- [ ] **Step 5: Resolve OpenCode configuration and required skills**

Run:

```bash
opencode debug config > /tmp/garmin-sync-opencode-config.json
python -c 'import json; c=json.load(open("/tmp/garmin-sync-opencode-config.json")); p=c["plugin"]; assert "@warp-dot-dev/opencode-warp" in p; assert "superpowers@git+https://github.com/obra/superpowers.git#v6.1.1" in p'
opencode debug skill | rg 'brainstorming|writing-plans|using-git-worktrees|subagent-driven-development|finishing-a-development-branch'
```

Expected: the JSON assertion passes and all five bridge-required skills appear. This task changes only global user configuration, so it has no Git commit.

### Task 2: Initialize and version the OpenSpec project

**Files:**
- Modify: `.gitignore`
- Create: `openspec/config.yaml`
- Create: `openspec/schemas/superpowers-bridge/UPSTREAM.md`
- Create from pinned upstream: `openspec/schemas/superpowers-bridge/{README.md,README.zh-TW.md,VERSION,schema.yaml}`
- Create from pinned upstream: `openspec/schemas/superpowers-bridge/templates/{brainstorm,proposal,design,spec,tasks,plan,verify,retrospective}.md`
- Create from pinned upstream: `openspec/schemas/superpowers-bridge/templates/adopters/{CLAUDE.md.fragment.md,CLAUDE.md.fragment.zh-TW.md}`
- Generate and ignore: `.codex/`, `.opencode/`
- Track: `docs/superpowers/plans/2026-07-13-openspec-superpowers-integration.md`

**Interfaces:**
- Consumes: Task 1's custom OpenSpec workflow profile.
- Produces: a healthy OpenSpec root, locally generated adapters, and a resolvable optional bridge schema.

- [ ] **Step 1: Add only the two generated adapter roots to `.gitignore`**

Use `apply_patch` to append:

```gitignore

# Generated OpenSpec adapters
.codex/
.opencode/
```

Run `git diff -- .gitignore`. Expected: only those two ignore patterns and their comment are added.

- [ ] **Step 2: Initialize OpenSpec with the pinned nvm runtime**

Run:

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 22.20.0
openspec init . --tools codex,opencode --profile custom
```

Expected: `openspec/config.yaml`, `openspec/specs/`, `openspec/changes/archive/`, `.codex/`, and `.opencode/` exist; the generated adapters include all nine selected workflows.

- [ ] **Step 3: Replace the minimal project config with approved context**

Use `apply_patch` so `openspec/config.yaml` is exactly:

```yaml
schema: spec-driven

context: |
  Training Sync is a Python 3.10+ setuptools project exposing the
  `training-sync` console command. Run tests with `python -m pytest`.

  Garmin Connect is the source of truth for completed activities. An existing
  Obsidian daily note is the intermediate representation. Weight x Reps is a
  reconciled full-day destination whose writes must be verified by read-back.

  Implement changes test-first. Never create a missing daily note, silently
  create an ambiguous Weight x Reps exercise, or report synchronization success
  before the saved remote fields have been read back and verified.

rules:
  specs:
    - Use SHALL or MUST for normative requirements and include at least one testable scenario per requirement.
    - Preserve strength activities and every Garmin activity for the requested day.
  tasks:
    - Order tasks by dependency and use checkbox syntax for every implementation task.
    - Require a failing test before production changes and a focused passing test afterward.
  plan:
    - Include exact file paths, commands, expected outcomes, and Conventional Commit checkpoints.
```

- [ ] **Step 4: Retrieve and verify the pinned community schema source**

Run outside the repository tree:

```bash
rm -rf /tmp/openspec-schemas-pinned
git clone https://github.com/JiangWay/openspec-schemas.git /tmp/openspec-schemas-pinned
git -C /tmp/openspec-schemas-pinned checkout f5d40404856ad0f4ce9eb482cbb0e28cf434411f
test "$(git -C /tmp/openspec-schemas-pinned rev-parse HEAD)" = "f5d40404856ad0f4ce9eb482cbb0e28cf434411f"
```

Expected: the final `test` exits 0. Do not copy `.git` or files outside upstream `superpowers-bridge/`.

- [ ] **Step 5: Vendor upstream-owned schema files byte-for-byte**

Read each file from `/tmp/openspec-schemas-pinned/superpowers-bridge/` and add the exact content with `apply_patch` at the corresponding path under `openspec/schemas/superpowers-bridge/`. Include every upstream file listed in this task's Files block and do not edit its content.

Verify the copy without modifying either tree:

```bash
diff -ru --exclude UPSTREAM.md /tmp/openspec-schemas-pinned/superpowers-bridge openspec/schemas/superpowers-bridge
```

Expected: exit code 0 and no diff output.

- [ ] **Step 6: Record provenance without changing the upstream package**

Create `openspec/schemas/superpowers-bridge/UPSTREAM.md` with `apply_patch`:

```markdown
# Upstream provenance

- Repository: <https://github.com/JiangWay/openspec-schemas>
- Path: `superpowers-bridge/`
- Commit: `f5d40404856ad0f4ce9eb482cbb0e28cf434411f`
- Vendored: `2026-07-13`

All other files in this directory are copied byte-for-byte from that source.
```

- [ ] **Step 7: Validate schema resolution, adapter ignores, and regression tests**

Run:

```bash
openspec schema which superpowers-bridge
openspec schema validate superpowers-bridge --verbose
openspec schemas --json
git check-ignore -v .codex .opencode
python -m pytest -q
```

Expected: the bridge resolves inside `openspec/schemas/`; validation succeeds; the schema list contains `spec-driven` and `superpowers-bridge`; both adapter roots are ignored; pytest reports `97 passed`.

- [ ] **Step 8: Commit only the repository bootstrap**

Run:

```bash
git add .gitignore openspec/config.yaml openspec/schemas docs/superpowers/plans/2026-07-13-openspec-superpowers-integration.md
git diff --cached --check
git diff --cached --name-only
git commit -m "chore(openspec): initialize codex and opencode workflows"
```

Expected: the cached file list contains no `README.md`, no pilot change, and no generated `.codex/` or `.opencode/` file.

### Task 3: Migrate the active design into the bridge pilot

**Files:**
- Modify: `docs/superpowers/specs/2026-07-04-one-day-sync-cycling-design.md`
- Create: `openspec/changes/add-one-day-multi-activity-sync/.openspec.yaml`
- Create: `openspec/changes/add-one-day-multi-activity-sync/{brainstorm,proposal,design,tasks,plan}.md`
- Create: `openspec/changes/add-one-day-multi-activity-sync/specs/daily-multi-activity-sync/spec.md`
- Create: `openspec/changes/add-one-day-multi-activity-sync/specs/weightxreps-cardio-sync/spec.md`

**Interfaces:**
- Consumes: the optional schema from Task 2 and the approved decisions in `2026-07-13-openspec-superpowers-integration-design.md`.
- Produces: a bridge-selected change ready through `plan.md`, with implementation and post-implementation artifacts still pending.

- [ ] **Step 1: Scaffold the change with the optional schema**

Run:

```bash
openspec new change add-one-day-multi-activity-sync \
  --schema superpowers-bridge \
  --goal "Synchronize every Garmin activity for one day into the existing daily note and structured Weight x Reps rows" \
  --json
```

Expected: `.openspec.yaml` records `schema: superpowers-bridge` and `created: 2026-07-13`; project `openspec/config.yaml` remains `schema: spec-driven`.

- [ ] **Step 2: Write `brainstorm.md` as the approved decision record**

Run `openspec instructions brainstorm --change add-one-day-multi-activity-sync --json`, then use `apply_patch` to write a raw decision log containing these resolved choices:

1. Adopt OpenSpec change-first and migrate only the active legacy design.
2. Synchronize all Garmin activities for the date, not exactly one.
3. Require an existing daily note and `--yes` for a non-empty training section.
4. Preserve strength and all cardio when replacing the Weight x Reps day.
5. Encode cardio with distance as `type: 2` plus real time/distance; encode cardio without distance as `type: 1` plus real time.
6. Store unsupported Garmin metrics in comment `c`.
7. Verify `type`, `t`, `d`, and `dunit` by read-back.
8. Preflight all inputs, update the daily before Weight x Reps, and retain the daily on remote failure.

Expected: `openspec status --change add-one-day-multi-activity-sync --json` marks `brainstorm` complete and makes `proposal` plus `design` ready.

- [ ] **Step 3: Extract the concise proposal**

Run `openspec instructions proposal --change add-one-day-multi-activity-sync --json`, then create `proposal.md` with:

- **Why:** the dispatcher does not implement integrated day sync, cycling blocks break current Weight x Reps parsing, and one day may contain multiple activities.
- **What Changes:** dispatch `sync DATE`, reconcile all Garmin activities into the existing daily, generate structured Weight x Reps cardio rows, replace safely, and verify read-back.
- **New Capabilities:** `daily-multi-activity-sync` and `weightxreps-cardio-sync`.
- **Modified Capabilities:** none, because `openspec/specs/` is initially empty.
- **Impact:** CLI, one-day use case, Garmin-to-daily rendering, Weight x Reps parser/JEditor/client, tests, and later README documentation.

Expected: capability names exactly match the two spec directories.

- [ ] **Step 4: Transform approved choices into `design.md`**

Run `openspec instructions design --change add-one-day-multi-activity-sync --json`, then create the structured design with current gaps, goals/non-goals, stable activity ordering, one combined daily section, preflight-before-write, one `--yes` contract, full-day strength-preserving reconstruction, structured `type: 1`/`type: 2` mapping, comment metadata, read-back verification, and the approved partial-failure policy. Include migration/rollback and state that no open questions remain.

Expected: the design explains why each choice was selected and never claims the feature is implemented.

- [ ] **Step 5: Write testable delta specs for both capabilities**

Run `openspec instructions specs --change add-one-day-multi-activity-sync --json`, then create both files using `## ADDED Requirements`, `### Requirement:`, and exact `#### Scenario:` headings.

`daily-multi-activity-sync/spec.md` must normatively cover:

- Fetch and stably order every Garmin activity for the target date.
- Fail before writes when none exist.
- Require an existing daily note.
- Render all activities into one `## 🏃 Training` section.
- Require `--yes` before replacing non-empty daily content.
- Complete every preflight before the first write.
- Keep the updated daily and report partial failure if Weight x Reps fails.

`weightxreps-cardio-sync/spec.md` must normatively cover:

- Preserve strength and every cardio activity in the full-day replacement.
- Reject unresolved or ambiguous exercises before writes.
- Encode distance cardio as `type: 2` with milliseconds and encoded distance/unit.
- Encode duration-only cardio as `type: 1` with milliseconds.
- Record activity name, heart rate, elevation, power, calories, and training
  load in `c` whenever Garmin provides them.
- Require `--yes` before replacing an existing remote day.
- Read back and compare exercise, `type`, `t`, `d`, and `dunit` before success.
- Return expected versus observed details on a verification mismatch.

Every requirement needs at least one WHEN/THEN scenario, including no-activity, missing-daily, multiple-activity, existing-content, mixed strength/cardio, unknown-exercise, duration-only, and read-back-mismatch cases.

- [ ] **Step 6: Create dependency-ordered `tasks.md`**

Run `openspec instructions tasks --change add-one-day-multi-activity-sync --json`, then create this exact task structure:

```markdown
## 1. CLI contract and orchestration preflight
- [ ] 1.1 Add failing CLI tests for `sync DATE [--yes]` dispatch and validation.
- [ ] 1.2 Add failing use-case tests for zero, one, and multiple activities plus no-write preflight failures.
- [ ] 1.3 Implement the minimal CLI and orchestration contract.

## 2. Daily multi-activity rendering
- [ ] 2.1 Add failing renderer and vault tests for stable multi-activity replacement and confirmation.
- [ ] 2.2 Implement combined rendering and existing-daily replacement.

## 3. Structured Weight x Reps cardio rows
- [ ] 3.1 Add failing parser/domain tests for duration, distance, unit, set type, and comments.
- [ ] 3.2 Implement `type: 1` and `type: 2` JEditor conversion with real fields.
- [ ] 3.3 Add failing mixed-day tests proving strength and every cardio activity are preserved.

## 4. Remote reconciliation and verification
- [ ] 4.1 Add failing client tests for confirmation, full-day replacement, and structured read-back comparison.
- [ ] 4.2 Implement remote replacement and expected-versus-observed verification errors.
- [ ] 4.3 Add orchestration tests proving the daily is retained after a remote failure and retries are idempotent.

## 5. Documentation and end-to-end verification
- [ ] 5.1 Update README usage and remove the obsolete marker-only limitation.
- [ ] 5.2 Run focused tests, the full suite, and a read-only known-day preview.
```

- [ ] **Step 7: Generate the feature micro-plan with Superpowers**

Run `openspec instructions plan --change add-one-day-multi-activity-sync --json`, invoke `superpowers:writing-plans`, and redirect its output to `openspec/changes/add-one-day-multi-activity-sync/plan.md` instead of `docs/superpowers/plans/`.

The feature plan must map every task above to exact current paths under `src/training_sync/` and `tests/`, use failing-test/pass cycles, define consistent data types/signatures, include exact commands, and add Conventional Commit checkpoints. It must not execute implementation.

- [ ] **Step 8: Add the migration notice to the legacy active design**

Use `apply_patch` immediately below its title:

```markdown
> [!NOTE]
> Migrated to OpenSpec as `add-one-day-multi-activity-sync`. The OpenSpec
> change is the source of truth for current requirements and planning; this
> document is retained as historical context.
```

Do not rewrite or delete legacy content.

- [ ] **Step 9: Validate and commit the complete pilot plan**

Run:

```bash
openspec status --change add-one-day-multi-activity-sync --json
openspec validate add-one-day-multi-activity-sync --type change --strict --no-interactive
git add docs/superpowers/specs/2026-07-04-one-day-sync-cycling-design.md openspec/changes/add-one-day-multi-activity-sync
git diff --cached --check
git diff --cached --name-only
git commit -m "docs(openspec): migrate multi-activity sync change"
```

Expected: status shows artifacts through `plan` complete. The graph may show
`verify` as ready because it depends structurally on `plan`, but the bridge's
implementation-evidence precheck forbids generating it before apply;
`retrospective` remains blocked on `verify`. The cached list excludes
`README.md`.

### Task 4: Verify the completed integration without external writes

**Files:**
- Read only: repository and global configuration produced by Tasks 1-3.

**Interfaces:**
- Consumes: both integration commits and global configuration.
- Produces: evidence that OpenSpec, both adapters, OpenCode Superpowers, the pilot change, Git isolation, and the Python project are healthy.

- [ ] **Step 1: Run complete OpenSpec health checks**

Run:

```bash
openspec doctor --json
openspec schema validate superpowers-bridge --json
openspec validate --all --strict --no-interactive --json
openspec status --change add-one-day-multi-activity-sync --json
```

Expected: doctor reports a healthy local root; schema and all available items are valid; the pilot uses `superpowers-bridge` and is complete through `plan` only.

- [ ] **Step 2: Verify default-versus-pilot schema isolation**

Run:

```bash
rg -n '^schema:' openspec/config.yaml openspec/changes/add-one-day-multi-activity-sync/.openspec.yaml
openspec schema which spec-driven
openspec schema which superpowers-bridge
```

Expected: project default is `spec-driven`, pilot metadata is `superpowers-bridge`, and the bridge resolves from the repository-local schema directory.

- [ ] **Step 3: Verify both generated adapters and global OpenCode skills**

Run:

```bash
git check-ignore -v .codex .opencode
find .codex .opencode -type f | sort
opencode debug config > /tmp/garmin-sync-opencode-config.json
opencode debug skill | rg 'brainstorming|writing-plans|using-git-worktrees|subagent-driven-development|finishing-a-development-branch'
```

Expected: both roots are ignored, their generated files cover the nine selected OpenSpec workflows, OpenCode resolves both plugins, and all bridge prerequisites are present.

- [ ] **Step 4: Run project regression tests**

Run `python -m pytest -q`. Expected: `97 passed` with no new failure.

- [ ] **Step 5: Prove Git isolation and commit boundaries**

Run:

```bash
git status --short
git log -3 --oneline
git show --stat --oneline HEAD~1
git show --stat --oneline HEAD
```

Expected:

- `README.md` remains the only pre-existing modified file.
- No OpenSpec or adapter file is untracked.
- The bootstrap commit excludes the active change and README.
- The migration commit excludes README and global user configuration.

- [ ] **Step 6: Report completion and deferred work**

Report the two new commit IDs, OpenSpec/OpenCode versions, global profile and workflow list, schema provenance commit, test result, pilot artifact status, and the untouched README change. Explicitly state that no feature implementation or live Garmin/Obsidian/Weight x Reps write occurred and that `verify.md`/`retrospective.md` remain intentionally deferred.
