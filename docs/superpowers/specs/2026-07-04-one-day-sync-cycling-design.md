# One-Day Sync and Cycling Support Design

> [!NOTE]
> Migrated to OpenSpec as `add-one-day-multi-activity-sync`. The OpenSpec
> change is the source of truth for current requirements and planning; this
> document is retained as historical context.

## Context

`training-sync` is intended to synchronize one training day across Garmin Connect, the Obsidian vault, and Weight x Reps.

The current CLI already exposes a top-level command shape:

```bash
training-sync sync YYYY-MM-DD
```

but the dispatcher does not handle it. Running the command prints help instead of synchronizing the day.

The manual sync performed for `2026-07-03` exposed a second gap: Garmin cycling/Zwift activities are stored in the daily note as metric blocks such as:

```text
2026-07-03

#Virtual_ride
27.95km
@ Duration: 01:00:20.0
@ Avg HR: 148
@ Max HR: 166
@ Training Load: 83
@ Elev Gain: 158
@ Avg Power: 136
@ Calories: 472
```

`training-sync weightxreps preview` currently treats `27.95km` as a Weight x Reps set line and fails because it only supports `WEIGHT_X_REPS` rows like `59kg x 10`.

Weight x Reps already has a user-specific precedent for cycling:

- Date: `2026-07-01`
- Exercise: `Cycling`
- Exercise ID: `157740`
- Saved set row: `{"v": 0, "r": 1, "s": 1, "type": 2}`

This spec turns those discoveries into first-class CLI behavior.

## Goals

- Make `training-sync sync YYYY-MM-DD` perform the complete one-day flow.
- Keep Garmin Connect as the source of truth for completed activity metrics.
- Update only the existing Obsidian daily note for the target date.
- Preserve the current daily-note training block style for endurance activities.
- Push Zwift/cycling daily-note blocks to Weight x Reps as `Cycling` `type: 2` rows.
- Verify Weight x Reps writes by reading the target day back.
- Avoid broad refactors; implement the smallest stable path that removes the manual work.

## Non-Goals

- Do not create missing daily notes automatically.
- Do not support arbitrary distance/time-based Weight x Reps exercise types beyond cycling in this slice.
- Do not change Garmin strength import behavior.
- Do not infer or create new Weight x Reps exercises for cycling; `Cycling` must resolve to an existing exercise ID.
- Do not replace existing strength parsing semantics for `kg x reps` or `BW x reps`.
- Do not add browser automation for this workflow.

## User Flow

The intended recurring command is:

```bash
training-sync sync 2026-07-03
```

Expected behavior:

1. Fetch Garmin activities for `2026-07-03`.
2. Require exactly one matching completed activity unless future flags add selection.
3. Render the activity into the established daily-note training format.
4. Replace or insert the `## 🏃 Training` section content in the existing daily note.
5. Convert the daily-note training block into Weight x Reps rows.
6. Push those rows to Weight x Reps with replacement enabled.
7. Read the Weight x Reps day back and verify the expected rows exist.
8. Print a concise success summary naming Garmin activity title, daily path, and Weight x Reps result.

## Garmin Activity Selection

For this first implementation, `sync` should be intentionally conservative:

- If Garmin returns no activities, exit with a clear message.
- If Garmin returns exactly one activity, sync it.
- If Garmin returns multiple activities, exit before editing the vault or Weight x Reps.

The multiple-activity case can later gain flags like `--activity-id` or `--type`, but it should not guess in this slice.

## Daily Note Update

Use the existing vault helpers:

- `training_sync.vault.daily.daily_note_path`
- `training_sync.vault.training_block.replace_training_section`

The daily note must already exist.

For the `2026-07-03` Zwift example, the rendered section should look like:

```markdown
- Zwift - Garmin UNBOUND Gravel Training Plan | Time To Get Dirty!. Garmin: 27.95 km, 1:00:20 total, 158 m desnivel, 148 bpm promedio, 166 bpm máximo, 136 W promedio, 472 calorías.
```text
2026-07-03

#Virtual_ride
27.95km
@ Duration: 01:00:20.0
@ Avg HR: 148
@ Max HR: 166
@ Training Load: 83
@ Elev Gain: 158
@ Avg Power: 136
@ Calories: 472
```
```

Historical notes use both `#Cycling` and `#Virtual_ride`; the renderer may preserve Garmin's `activityType.typeKey` as today, but the Weight x Reps parser should normalize either tag to the Weight x Reps exercise `Cycling`.

## Weight x Reps Cardio Representation

Extend the parsed training model to support set type:

```python
ParsedSetLine(
    weight_kg=0.0,
    reps=[1],
    uses_bodyweight=False,
    set_type=2,
)
```

Default behavior stays unchanged:

- `kg x reps` parses as `set_type=0`.
- `BW x reps` parses as `set_type=0`.
- JEditor rows default to `type: 0`.

Cycling behavior:

- `#Virtual_ride` with a following line ending in `km` parses as exercise `Cycling`.
- `#Cycling` with a following line ending in `km` parses as exercise `Cycling`.
- The distance value is not encoded into Weight x Reps in this slice, because the observed Weight x Reps row uses only a marker set.
- The generated JEditor row is:

```python
{
    "eid": 157740,
    "erows": [
        {"w": {"v": 0.0, "lb": 0}, "r": 1, "s": 1, "type": 2}
    ],
}
```

## Weight x Reps Verification

`WeightxRepsClient.verify_day` currently assumes saved rows are valid only when all saved sets have `type == 0`.

Change verification to compare expected set types from the rows sent to `save_jeditor`:

- A strength row with `type: 0` must read back with `type: 0`.
- A cycling row with `type: 2` must read back with `type: 2`.
- Missing exercise blocks still fail verification.
- Saved blocks with missing set types still fail verification.

This avoids weakening verification while allowing non-strength rows.

## CLI Orchestration

Add dispatcher support for:

```bash
training-sync sync YYYY-MM-DD
```

The command should call a CLI wrapper such as:

```python
def sync_day_cli(date: str) -> None:
    ...
```

The wrapper should:

- Build a Garmin client using existing authentication.
- Build a Weight x Reps client using existing token handling.
- Load Weight x Reps mappings and optional user ID using existing config helpers.
- Run the one-day sync.
- Print a compact JSON or text result.

The implementation may introduce small adapter classes for Garmin and Weight x Reps if that keeps `sync_day` testable without live services.

## Proposed File Changes

- `src/training_sync/cli.py`
  - Dispatch the `sync` command.
  - Add `sync_day_cli`.

- `src/training_sync/use_cases/sync_day.py`
  - Replace the current skeleton with a real one-day orchestration use case.
  - Keep service dependencies injectable for tests.

- `src/training_sync/renderers/weightxreps_text.py`
  - Add `ParsedSetLine.set_type`.
  - Parse cycling distance blocks into a cycling marker set.

- `src/training_sync/weightxreps/jeditor.py`
  - Preserve `ParsedSetLine.set_type` in `erows`.

- `src/training_sync/weightxreps/client.py`
  - Verify expected set types instead of hard-coding `type == 0`.

- `README.md`
  - Document `training-sync sync YYYY-MM-DD`.
  - Document the current cycling limitation: distance is stored in the vault, while Weight x Reps receives the canonical cycling marker row.

## Test Plan

Add focused tests before production code:

- `tests/test_training_sync_cli.py`
  - `training-sync sync 2026-07-03` dispatches to `sync_day_cli("2026-07-03")`.
  - `sync_day_cli` exits clearly when Weight x Reps auth tokens are missing.

- `tests/test_weightxreps_text.py`
  - `#Virtual_ride` plus `27.95km` parses as exercise `Cycling` with `set_type=2`.
  - `#Cycling` plus `27.95km` parses as exercise `Cycling` with `set_type=2`.
  - Existing `kg x reps` and `BW x reps` parsing still returns `set_type=0`.

- `tests/test_weightxreps_jeditor.py`
  - Cardio parsed set lines render to JEditor rows with `type: 2`.
  - Strength set rows still render to `type: 0`.

- `tests/test_weightxreps_client.py`
  - `verify_day` accepts saved cycling rows when expected rows use `type: 2`.
  - `verify_day` still rejects missing or mismatched set types.

- `tests/test_use_case_sync_day.py`
  - The orchestrator updates the vault before pushing Weight x Reps.
  - If Garmin has multiple activities, the orchestrator aborts before any writes.
  - If the daily note is missing, the orchestrator aborts before Weight x Reps writes.

## Manual Verification

After automated tests pass, run a dry sequence on a known day before using a fresh day:

```bash
training-sync garmin fetch 2026-07-03
training-sync weightxreps preview 2026-07-03
```

Then run the integrated command on a date whose daily note can be safely updated:

```bash
training-sync sync 2026-07-03
```

Expected final checks:

- The daily note has one training block for the Garmin activity.
- `training-sync weightxreps preview 2026-07-03` no longer crashes on `27.95km`.
- Weight x Reps read-back contains exercise `Cycling` with a set of `type: 2`.

## Open Questions

- Should `sync` replace an existing non-empty training section automatically, or require `--yes` once a section already contains content?
- Should `sync` offer `--activity-id` in this same slice, or wait until the first multiple-activity day forces the need?
- Should cycling distance eventually be encoded in Weight x Reps if the API supports a richer distance/time row shape?

## Recommendation

Implement the conservative slice first:

- one activity only,
- existing daily only,
- replace Weight x Reps day with verification,
- cycling marker row only,
- no automatic exercise creation.

That removes the current manual workaround while keeping the command boring and predictable.
