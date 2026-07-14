# Retrospective: add-one-day-multi-activity-sync

> Written: 2026-07-14 (after verify passed)  
> Commit range: `b3f1a46..a227c74`  
> Worktree: `/Volumes/ssd1/dev/garmin-sync/.worktrees/add-one-day-multi-activity-sync`

---

## 0. Evidence

- **Commit range**: `b3f1a46..a227c74` (19 commits)
- **Diff size**: +3181 / -137 lines across 24 files
- **Tasks done**: 13/13 (`tasks.md` has 13 checked and 0 unchecked tasks)
- **Active hours**: 1.4 hours measured from first implementation commit at 00:34 to verification commit at 01:56 (-04)
- **Subagent dispatches**: 16 distinct agents, 26 implementation/review/fix turns including re-reviews
- **New external dependencies**: none
- **Bugs encountered post-merge**: none — the branch has not been merged; all defects below were found before merge
- **OpenSpec validate state at archive**: pass at retrospective write-time (1/1 item valid); archive not yet run
- **Test coverage signal**: 215 pytest tests passed on final HEAD; authenticated known-day read-only fetch/preview exited 0

Commit chain (chronological):

```text
c0e54d2 feat(sync): add multi-activity preflight contract
bfd1baa docs(openspec): mark sync preflight complete
14b058e feat(sync): render combined daily activities
db9b34e fix(sync): carry rounded activity times
fbade40 docs(openspec): mark daily rendering complete
f1b82d1 feat(weightxreps): encode structured cardio rows
7b0941f fix(sync): reject unsupported cardio plans
e1e7cb8 docs(openspec): mark cardio encoding complete
287f881 feat(sync): verify full remote day replacement
1de38a3 fix(sync): preserve full day across retries
a9893f3 docs(openspec): mark remote reconciliation complete
12d623e docs(sync): document multi-activity reconciliation
3fd80ea fix(preview): normalize virtual rides to cycling
c4229b1 docs(sync): clarify required training heading
d62cc3f docs(openspec): mark multi-activity sync complete
ae8e8cf fix(sync): reconcile complete remote training day
73e93b3 fix(sync): enforce activity round trips
3043588 fix(sync): support known Garmin activity aliases
a227c74 docs(openspec): record implementation verification
```

---

## 1. Wins

- [evidence: `tasks.md`, `a227c74`] The OpenSpec/Superpowers bridge completed the full artifact-to-code cycle: 13/13 tasks, verification PASS, and no unreviewed implementation task.
- [evidence: commits `c0e54d2`, `14b058e`, `f1b82d1`, `287f881`] The five-task decomposition kept CLI/preflight, daily rendering, cardio encoding, remote verification, and documentation separately testable and reviewable.
- [evidence: `tests/test_use_case_sync_day.py:464`, commit `1de38a3`] The review loop upgraded “idempotent retry” from replaying an in-memory plan to a real fresh-process retry that reconstructs from durable state.
- [evidence: commits `ae8e8cf`, `73e93b3`] Destructive remote replacement became materially safer than the initial plan: remote bodyweight/type-0 strength is reconciled, lossy shapes abort before writes, and the retained daily must round-trip losslessly.
- [evidence: `src/training_sync/domain/activity_classification.py`, commit `3043588`] One shared activity classifier now keeps integrated sync, daily tags, and standalone preview aligned across observed Garmin aliases.
- [evidence: final reviewer verdict, 215 pytest tests] Fresh implementation/reviewer agents repeatedly found non-obvious boundary failures before merge; the final whole-branch review returned “Ready to merge: Yes” with no remaining findings.
- [evidence: Task 5 report, `verify.md`] The known 2026-07-03 Garmin/Weight x Reps preview proved the corrected `Cycling` row (`eid=157740`, `type=2`, `t=3620000`, `d.val=279500000`) without external writes.

## 2. Misses

- 🔴 [blocking | evidence: final branch review before `ae8e8cf`] The initial “full-day replacement” preserved strength only from the vault and treated the remote day as a boolean. That left a real remote strength/bodyweight data-loss path until the final whole-branch review forced explicit remote reconciliation.
- 🔴 [blocking | evidence: Task 4 review before `1de38a3`] The first retry test reused the same `SyncPlan`, which cannot exist in a new process. It masked loss of parseable strength after the daily replacement.
- 🟡 [painful | evidence: commits `73e93b3`, `3043588`] Activity naming evolved through three inconsistent paths (`sync_day`, renderer, preview) before being centralized. The first central table then proved too narrow for common Garmin running/cycling aliases.
- 🟡 [painful | evidence: commits `db9b34e`, `7b0941f`, `3fd80ea`, `c4229b1`] Task-level reviews repeatedly found boundary behavior absent from the initial micro-plan: time carry, integrated no-create enforcement, standalone `Virtual_ride`, and exact heading documentation.
- 🟡 [painful | evidence: 19 commits, 26 subagent turns] The cycle required more review/fix waves than expected. The extra cost bought safety, but the initial design should have specified remote snapshot reconciliation and cross-path round-trip invariants earlier.
- 📌 [nit | evidence: permission errors invoking `task-brief` and `review-package`] The bundled SDD helper scripts lacked executable bits, requiring `bash ...` plus explicit output paths. This added avoidable controller friction but did not affect product code.

## 3. Plan deviations

| Plan task | What changed | Why |
|---|---|---|
| Preflight | Added timestamp validation, exact heading matching, structured CLI resolution errors, and a full remote snapshot boundary | Final review showed malformed ordering keys, near-match headings, and remote-only strength were destructive preflight gaps. |
| Daily rendering | Added rounded-tenths carry handling and a durable parseable strength/bodyweight block | Real retry convergence required the retained daily to be sufficient for a new process. |
| Cardio rows | Replaced separate activity-name logic with a shared classifier covering observed Garmin families | Renderer, integrated sync, and preview otherwise produced incompatible exercise names or silently omitted activities. |
| Remote verification | Expanded verification from exercise plus cardio fields to bodyweight, type-0 strength fields, order, and submitted comments | “Full-day preserved” was not proven by cardio-only read-back checks. |
| Remote preservation | Added lossless render/parse validation and aborts for weighted-bodyweight, pounds, comments, and high-precision shapes that the daily grammar cannot represent | A lossy preserved snapshot would make a fresh retry diverge or corrupt the remote day. |
| Documentation/preview | Fixed standalone `Virtual_ride` normalization and documented the exact heading plus reconciliation safety | The required known-day preview exposed a real cross-path mapping inconsistency. |

## 4. Skill / workflow compliance

| Skill | Used |
|---|---|
| `superpowers:brainstorming` | ✓ — decisions captured in `brainstorm.md` before implementation |
| `superpowers:writing-plans` | ✓ — micro-plan in `plan.md` drove all five tasks |
| `superpowers:using-git-worktrees` | ✓ — isolated branch/worktree created before Task 1 |
| `superpowers:subagent-driven-development` | ✓ — fresh implementer and reviewer gates per task, durable ledger used |
| (transitive) `superpowers:test-driven-development` | ✓ — every implementation/fix report includes RED then GREEN evidence |
| (transitive) `superpowers:requesting-code-review` | ✓ — task reviews plus repeated whole-branch review |
| `openspec-verify-change` | ✓ — `verify.md` at `a227c74`, Overall Decision PASS |
| `superpowers:finishing-a-development-branch` | ⏳ pending by schema order — invoked only after this retrospective and archive |

`finishing-a-development-branch` was not skipped. The schema explicitly requires retrospective and archive before the branch-finishing/PR step, so it is downstream and not yet reachable at retrospective write-time.

### Deliberately Skipped Skills

None. Every reachable apply-phase skill was used; the only pending skill is sequenced after this artifact by the schema.

## 5. Surprises

- The official Weight x Reps prose documentation and the live client/server contract did not agree on distance shape. Runtime code proved save uses nested `d: {val, unit}` while read-back is flat `d`/`dunit`.
- A daily retained after partial failure was not automatically a retry-safe source. Multi-block loading, strength-only serialization, and round-trip validation were all required.
- A successful remote mutation plus matching cardio fields was insufficient evidence for “full-day” preservation; bodyweight and type-0 fields also had to be normalized and compared.
- “Synchronize all activities” required three distinct semantics: every Garmin activity is rendered locally, strength remains locally preserved, and supported non-strength activities map to canonical Weight x Reps exercises or fail before writes.
- Exact mapping tables are safer than broad heuristics, but too narrow a table is also a compatibility regression. Known Garmin families need explicit aliases plus cross-path tests.

## 6. Promote candidates → long-term learning

- [ ] 🔴 **Any full-day remote replacement must reconcile the actual remote preservation state, not just test whether the day is non-empty.** → **Promote to project agent guidance**
  > **Why**: The first implementation could overwrite remote bodyweight/type-0 strength when the daily was empty or stale.
  > **How to apply**: Before approving any destructive Weight x Reps replacement, load remote preserved state, reconcile by resolved exercise identity, and abort on divergence or lossiness.

- [ ] 🔴 **An idempotent retry test must rebuild state through the public command/use-case boundary in a fresh plan.** → **Promote to Superpowers review guidance**
  > **Why**: Re-applying the same in-memory `SyncPlan` passed while a real second command lost strength.
  > **How to apply**: For partial-failure workflows, invoke the public operation twice and require the second invocation to reconstruct identical durable output.

- [ ] 🟡 **Renderer, parser, preview, and remote mapping must share one canonical activity classifier.** → **Promote to project architecture guidance**
  > **Why**: Independent naming logic caused `Virtual_ride`, swimming, rowing, generic cardio, and Garmin family aliases to diverge.
  > **How to apply**: Add each observed Garmin `typeKey` once in the shared classifier and require classifier + integrated + render/preview round-trip tests.

- [ ] 🟡 **Preserved remote data must satisfy `parse(render(snapshot)) == snapshot` before a local intermediate is trusted.** → **Promote to project test guidance**
  > **Why**: Weighted-bodyweight and high-precision strength could not be represented losslessly in the current daily grammar.
  > **How to apply**: Run the invariant at remote adapter and orchestration boundaries; reject unsupported shapes before any write.

- [ ] 📌 **Retrospective skill-compliance templates should distinguish downstream-pending skills from deliberately skipped skills.** → **Promote to `superpowers-bridge` schema**
  > **Why**: The template expects `finishing-a-development-branch` to be marked used even though the same schema orders retrospective and archive before it.
  > **How to apply**: Add a `pending by graph order` state or move finishing compliance confirmation to a post-finish artifact/check.

- [ ] 📌 **Ship SDD helper scripts executable or document `bash <script> ... <explicit-output>` as the supported fallback.** → **Promote to Superpowers skill packaging**
  > **Why**: `task-brief`, `review-package`, and their internal `sdd-workspace` helper returned permission denied when invoked as documented.
  > **How to apply**: At plugin build time preserve executable bits and add a packaging test that invokes each helper directly.
