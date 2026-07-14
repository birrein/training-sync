# One-Day Multi-Activity Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `training-sync sync DATE [--yes]` so every Garmin activity for the date is rendered into the existing daily and reconciled as a verified, structured full-day Weight x Reps replacement.

**Architecture:** A preflight-first `sync_day` use case converts raw Garmin dictionaries into immutable `GarminActivity` values, sorts and renders them, resolves a complete Weight x Reps payload, and returns an immutable `SyncPlan` before either adapter writes. The apply half writes the daily first, replaces Weight x Reps second, and raises a structured partial-failure error without rolling the daily back. Existing vault and Weight x Reps modules remain the boundary adapters.

**Tech Stack:** Python 3.10+, standard-library dataclasses/protocols/pathlib/argparse, requests-backed Weight x Reps GraphQL client, pytest.

## Global Constraints

- Garmin Connect is the source of truth for every completed activity on the target date.
- The Obsidian daily and `## 🏃 Training` heading MUST already exist; never create either.
- A single `--yes` authorizes replacement of non-empty daily content and existing Weight x Reps content.
- Resolve every Weight x Reps exercise before the first write and never silently create an exercise.
- Cardio with distance uses `type: 2`; duration-only cardio uses `type: 1`; duration `t` is milliseconds.
- Preserve strength and every cardio activity in the full-day remote replacement.
- Report success only after exercise, `type`, `t`, `d`, and `dunit` read-back matches.
- If Weight x Reps write or verification fails, retain the updated daily and report partial failure.
- Use test-first cycles and keep project compatibility at Python 3.10+.

---

### Task 1: CLI contract and orchestration preflight

**Files:**
- Create: `src/training_sync/domain/garmin_activity.py`
- Modify: `src/training_sync/cli.py`
- Replace: `src/training_sync/use_cases/sync_day.py`
- Modify: `tests/test_training_sync_cli.py`
- Replace: `tests/test_use_case_sync_day.py`

**Interfaces:**
- Consumes: `garmin.get_activities_by_date(date, date) -> list[dict[str, object]]`, `daily_note_path(vault_root: Path, date: str) -> Path`, and a Weight x Reps gateway exposing `day_has_content`, exercise lookup, save, and read-back.
- Produces: `GarminActivity.from_garmin(raw: Mapping[str, object]) -> GarminActivity`; `SyncDependencies(garmin, weightxreps, vault_root, mappings, user_id)`; `preflight_sync_day(date: str, *, yes: bool, deps: SyncDependencies) -> SyncPlan`; `apply_sync_plan(plan: SyncPlan, *, deps: SyncDependencies) -> SyncResult`; `sync_day(date: str, *, yes: bool, deps: SyncDependencies) -> SyncResult`; and `sync_day_cli(date: str, yes: bool) -> None`.

- [ ] **Step 1: Add failing CLI dispatch and date-validation tests**

Add tests proving `sync 2026-07-03 --yes` calls `sync_day_cli("2026-07-03", yes=True)`, omission passes `False`, and invalid ISO dates exit through argparse before client construction:

```python
def test_training_sync_sync_dispatches_yes(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "sync_day_cli", lambda date, yes: calls.append((date, yes)))
    cli.main(["sync", "2026-07-03", "--yes"])
    assert calls == [("2026-07-03", True)]

def test_training_sync_sync_rejects_invalid_date():
    with pytest.raises(SystemExit) as exc:
        cli.main(["sync", "07-03-2026"])
    assert exc.value.code == 2
```

- [ ] **Step 2: Run the CLI tests and confirm RED**

Run: `python -m pytest tests/test_training_sync_cli.py -k 'sync_dispatches or sync_rejects' -v`

Expected: FAIL because `sync_day_cli` and the `--yes` sync option do not exist and the dispatcher prints help.

- [ ] **Step 3: Add failing activity normalization and preflight tests**

Replace the skeleton use-case test with fakes and assertions for zero, one, and multiple activities, deterministic `(start_time, activity_id)` ordering, missing daily, missing heading, unresolved exercises, existing content without `yes`, and no writes for every failure. Use this common raw fixture shape:

```python
def activity(activity_id: int, start: str, type_key: str = "running") -> dict:
    return {
        "activityId": activity_id,
        "activityName": f"Activity {activity_id}",
        "startTimeLocal": start,
        "activityType": {"typeKey": type_key},
        "duration": 1800.0,
        "distance": 5000.0,
    }

def test_preflight_orders_every_activity_and_does_not_write(tmp_path):
    deps = fake_dependencies(tmp_path, activities=[
        activity(30, "2026-07-03 18:00:00"),
        activity(20, "2026-07-03 07:00:00"),
        activity(10, "2026-07-03 07:00:00"),
    ])
    plan = preflight_sync_day("2026-07-03", yes=True, deps=deps)
    assert [item.activity_id for item in plan.activities] == [10, 20, 30]
    assert deps.writes == []
```

- [ ] **Step 4: Run preflight tests and confirm RED**

Run: `python -m pytest tests/test_use_case_sync_day.py -k 'preflight or zero or missing or multiple' -v`

Expected: FAIL because the current `sync_day` directly invokes two writes and has no activity model or preflight phase.

- [ ] **Step 5: Implement the minimal immutable activity and orchestration contracts**

Define the data contracts consistently:

```python
def _optional_int(value: object | None) -> int | None:
    return None if value is None else int(value)

def _optional_float(value: object | None) -> float | None:
    return None if value is None else float(value)

@dataclass(frozen=True)
class GarminActivity:
    activity_id: int
    name: str
    start_time: str
    type_key: str
    duration_ms: int
    distance_m: float | None
    average_hr: int | None = None
    max_hr: int | None = None
    elevation_gain_m: float | None = None
    average_power_w: int | None = None
    calories: int | None = None
    training_load: float | None = None

    @classmethod
    def from_garmin(cls, raw: Mapping[str, object]) -> "GarminActivity":
        activity_type = cast(Mapping[str, object], raw["activityType"])
        duration_seconds = float(raw["duration"])
        distance = raw.get("distance")
        return cls(
            activity_id=int(raw["activityId"]),
            name=str(raw["activityName"]),
            start_time=str(raw["startTimeLocal"]),
            type_key=str(activity_type["typeKey"]),
            duration_ms=round(duration_seconds * 1000),
            distance_m=float(distance) if distance is not None else None,
            average_hr=_optional_int(raw.get("averageHR")),
            max_hr=_optional_int(raw.get("maxHR")),
            elevation_gain_m=_optional_float(raw.get("elevationGain")),
            average_power_w=_optional_int(raw.get("avgPower")),
            calories=_optional_int(raw.get("calories")),
            training_load=_optional_float(raw.get("activityTrainingLoad")),
        )

@dataclass(frozen=True)
class SyncPlan:
    date: str
    activities: tuple[GarminActivity, ...]
    daily_path: Path
    original_daily: str
    updated_daily: str
    weightxreps_rows: tuple[dict[str, Any], ...]

@dataclass(frozen=True)
class SyncResult:
    date: str
    daily_path: Path
    activity_count: int
    weightxreps_verified: bool
```

In `cli.py`, validate with `date.fromisoformat`, add `sync_parser.add_argument("--yes", action="store_true")`, dispatch before the Garmin branches, and have `sync_day_cli` assemble existing auth/config adapters and print `json.dumps(asdict(result), default=str)`. Keep adapter construction after argument parsing so invalid input makes no network call.

- [ ] **Step 6: Run focused Task 1 tests and confirm GREEN**

Run: `python -m pytest tests/test_training_sync_cli.py tests/test_use_case_sync_day.py -v`

Expected: PASS, including zero/one/multiple activity and no-write preflight cases.

- [ ] **Step 7: Commit Task 1**

```bash
git add src/training_sync/domain/garmin_activity.py src/training_sync/cli.py src/training_sync/use_cases/sync_day.py tests/test_training_sync_cli.py tests/test_use_case_sync_day.py
git commit -m "feat(sync): add multi-activity preflight contract"
```

### Task 2: Daily multi-activity rendering

**Files:**
- Create: `src/training_sync/renderers/garmin_daily.py`
- Modify: `src/training_sync/vault/training_block.py`
- Modify: `src/training_sync/use_cases/sync_day.py`
- Create: `tests/test_garmin_daily_renderer.py`
- Modify: `tests/test_vault_training_block.py`
- Modify: `tests/test_use_case_sync_day.py`

**Interfaces:**
- Consumes: ordered `Sequence[GarminActivity]`, `extract_training_section(note_text: str) -> str`, and `replace_training_section(note_text: str, new_content: str) -> str`.
- Produces: `render_training_activities(date: str, activities: Sequence[GarminActivity]) -> str`; `training_section_has_content(note_text: str) -> bool`; and `write_daily(plan: SyncPlan) -> None` using UTF-8 `Path.write_text` only during apply.

- [ ] **Step 1: Add failing renderer tests for one combined ordered payload**

Test strength, running, distance cycling, and duration-only cardio. Assert exactly one activity summary/text block per input, the same order as input, one shared replacement payload (no repeated `## 🏃 Training` heading inside the payload), real duration, distance only when present, and available metadata lines.

```python
rendered = render_training_activities("2026-07-03", [morning_run, evening_ride])
assert rendered.index(morning_run.name) < rendered.index(evening_ride.name)
assert rendered.count("2026-07-03") == 2
assert "27.95km" in rendered
assert "@ Duration: 01:00:20.0" in rendered
```

- [ ] **Step 2: Add failing vault confirmation tests**

Extend `tests/test_vault_training_block.py` to prove whitespace-only content is empty, any non-whitespace content is non-empty, and replacement preserves both surrounding sections. Extend use-case tests so `yes=False` rejects non-empty content before writes while `yes=True` permits it.

- [ ] **Step 3: Run Task 2 tests and confirm RED**

Run: `python -m pytest tests/test_garmin_daily_renderer.py tests/test_vault_training_block.py tests/test_use_case_sync_day.py -v`

Expected: FAIL because the renderer and `training_section_has_content` do not exist.

- [ ] **Step 4: Implement combined rendering and daily replacement**

Use pure formatting helpers in `garmin_daily.py`; do not print. `preflight_sync_day` must read the existing daily once, reject a missing heading, inspect confirmation, render all activities, and call `replace_training_section` in memory. `apply_sync_plan` performs exactly one `plan.daily_path.write_text(plan.updated_daily, encoding="utf-8")` before any Weight x Reps save.

- [ ] **Step 5: Run Task 2 tests and confirm GREEN**

Run: `python -m pytest tests/test_garmin_daily_renderer.py tests/test_vault_training_block.py tests/test_use_case_sync_day.py -v`

Expected: PASS with stable multi-activity replacement and explicit confirmation behavior.

- [ ] **Step 6: Commit Task 2**

```bash
git add src/training_sync/renderers/garmin_daily.py src/training_sync/vault/training_block.py src/training_sync/use_cases/sync_day.py tests/test_garmin_daily_renderer.py tests/test_vault_training_block.py tests/test_use_case_sync_day.py
git commit -m "feat(sync): render combined daily activities"
```

### Task 3: Structured Weight x Reps cardio rows

**Files:**
- Modify: `src/training_sync/renderers/weightxreps_text.py`
- Modify: `src/training_sync/weightxreps/jeditor.py`
- Modify: `src/training_sync/use_cases/sync_day.py`
- Modify: `tests/test_weightxreps_text.py`
- Modify: `tests/test_weightxreps_jeditor.py`
- Modify: `tests/test_use_case_sync_day.py`

**Interfaces:**
- Consumes: rendered daily text, ordered `GarminActivity` values, existing `ParsedExercise`, and resolved `exercise_ids: dict[str, int]`.
- Produces: a single consistent `ParsedSetLine(weight_kg: float = 0.0, reps: tuple[int, ...] = (), uses_bodyweight: bool = False, set_type: int = 0, duration_ms: int | None = None, distance: float | None = None, distance_unit: int | None = None, comment: str | None = None)`; `_set_line_to_erow` mapping those values to `type`, `t`, `d`, `dunit`, and `c`; and `build_complete_training_day(date: str, preserved: ParsedTrainingDay, activities: Sequence[GarminActivity]) -> ParsedTrainingDay` that keeps preserved strength blocks plus every cardio activity.

- [ ] **Step 1: Add failing parser/domain tests**

Cover `#Running`/`#Cycling`/`#Virtual_ride`, `@ Duration`, distance lines, duration-only blocks, supported distance-unit encoding, comments with only supplied metrics, and unchanged `kg x reps`/`BW x reps` behavior. Assert `type=2` for distance cardio and `type=1` for duration-only cardio.

- [ ] **Step 2: Add failing JEditor conversion tests**

Use exact structured expectations:

```python
DISTANCE_UNIT_KILOMETERS = 0

distance_set = ParsedSetLine(
    set_type=2,
    duration_ms=3_620_000,
    distance=27.95,
    distance_unit=DISTANCE_UNIT_KILOMETERS,
    comment="Zwift Ride | Avg HR: 148 | Elev Gain: 158 m",
)
assert _set_line_to_erow(distance_set) == {
    "type": 2, "t": 3_620_000, "d": 27.95, "dunit": 0,
    "c": "Zwift Ride | Avg HR: 148 | Elev Gain: 158 m",
}
```

Also assert duration-only rows contain only `type`, `t`, and optional `c`, while strength payloads remain byte-for-byte equivalent to existing expectations.

- [ ] **Step 3: Run parser/JEditor tests and confirm RED**

Run: `python -m pytest tests/test_weightxreps_text.py tests/test_weightxreps_jeditor.py -v`

Expected: FAIL because the model has only strength fields and JEditor hard-codes `type: 0`.

- [ ] **Step 4: Implement structured parsing and conversion**

Parse cardio metadata as a whole block instead of passing distance or metadata lines to `_parse_set_line`. Centralize duration parsing and the Weight x Reps metric-unit encoding as `DISTANCE_UNIT_KILOMETERS = 0`. In `_set_line_to_erow`, branch on `set_type`: preserve current consolidated strength behavior for `0`; emit real `t` for `1`; emit `t`, `d`, and `dunit` for `2`; attach `c` only when non-empty.

- [ ] **Step 5: Add and satisfy mixed full-day preservation tests**

In `tests/test_use_case_sync_day.py`, seed preserved strength blocks and two Garmin cardio activities, then assert the planned rows contain each strength block unchanged and one separate cardio exercise block per activity. Add a retry fixture that constructs the same tuple of rows twice and assert equality.

- [ ] **Step 6: Run Task 3 tests and confirm GREEN**

Run: `python -m pytest tests/test_weightxreps_text.py tests/test_weightxreps_jeditor.py tests/test_use_case_sync_day.py -v`

Expected: PASS for duration, distance, unit, comments, strength preservation, and every cardio activity.

- [ ] **Step 7: Commit Task 3**

```bash
git add src/training_sync/renderers/weightxreps_text.py src/training_sync/weightxreps/jeditor.py src/training_sync/use_cases/sync_day.py tests/test_weightxreps_text.py tests/test_weightxreps_jeditor.py tests/test_use_case_sync_day.py
git commit -m "feat(weightxreps): encode structured cardio rows"
```

### Task 4: Remote reconciliation and verification

**Files:**
- Modify: `src/training_sync/weightxreps/client.py`
- Modify: `src/training_sync/use_cases/sync_day.py`
- Modify: `tests/test_weightxreps_client.py`
- Modify: `tests/test_use_case_sync_day.py`

**Interfaces:**
- Consumes: complete JEditor rows from Task 3 and `WeightxRepsClient.jeditor_day(date)`.
- Produces: `VerificationMismatch(expected: list[dict[str, Any]], observed: list[dict[str, Any]])`; `WeightxRepsClient.verify_day(date: str, rows: list[dict[str, Any]]) -> None` that returns normally only on an exact relevant-field match; and `PartialSyncFailure(date: str, daily_path: Path, cause: Exception)`.

- [ ] **Step 1: Extend the GraphQL query and add failing field-comparison tests**

Request `t`, `d`, `dunit`, and `c` in each saved set. Test matching strength/duration/distance blocks, missing exercise, missing field, wrong type/time/distance/unit, duplicate exercise blocks, and error payloads containing normalized expected and observed values.

```python
with pytest.raises(VerificationMismatch) as exc:
    client.verify_day("2026-07-03", expected_rows)
assert exc.value.expected[0]["erows"][0]["dunit"] == 0
assert exc.value.observed[0]["sets"][0]["dunit"] == 1
```

- [ ] **Step 2: Run client tests and confirm RED**

Run: `python -m pytest tests/test_weightxreps_client.py -k 'verify or structured or mismatch' -v`

Expected: FAIL because the query omits structured fields and `verify_day` returns a boolean after checking only block count and `type == 0`.

- [ ] **Step 3: Implement normalized expected-versus-observed verification**

Normalize only exercise `eid` and set `type`, `t`, `d`, and `dunit`, preserving set order within exercise blocks. Compare the complete expected block sequence; raise `VerificationMismatch` on any difference. Update existing callers that expect a boolean so they treat normal return as success and the exception as failure.

- [ ] **Step 4: Add failing confirmation, partial failure, and idempotent retry tests**

Assert remote content without `yes` fails in preflight before daily write; save is called after daily write; save exceptions and `VerificationMismatch` leave the written daily intact and raise `PartialSyncFailure`; retry generates and saves the same rows; and a matching read-back yields `weightxreps_verified=True`.

- [ ] **Step 5: Implement remote apply and partial-failure behavior**

`apply_sync_plan` must record the daily write, call `save_jeditor(list(plan.weightxreps_rows))`, then `verify_day(plan.date, rows)`. Wrap only remote save/read-back errors in `PartialSyncFailure`; never restore `original_daily`. The exception string must include date, daily path, original cause, and expected/observed details when present.

- [ ] **Step 6: Run Task 4 tests and confirm GREEN**

Run: `python -m pytest tests/test_weightxreps_client.py tests/test_use_case_sync_day.py tests/test_weightxreps_push.py -v`

Expected: PASS for full-day replacement, confirmation, structured verification, partial failure, and idempotent retry.

- [ ] **Step 7: Commit Task 4**

```bash
git add src/training_sync/weightxreps/client.py src/training_sync/use_cases/sync_day.py tests/test_weightxreps_client.py tests/test_use_case_sync_day.py tests/test_weightxreps_push.py
git commit -m "feat(sync): verify full remote day replacement"
```

### Task 5: Documentation and end-to-end verification

**Files:**
- Modify: `README.md`
- Test: `tests/test_training_sync_cli.py`
- Test: `tests/test_use_case_sync_day.py`
- Test: `tests/test_weightxreps_text.py`
- Test: `tests/test_weightxreps_jeditor.py`
- Test: `tests/test_weightxreps_client.py`

**Interfaces:**
- Consumes: completed `training-sync sync DATE [--yes]` behavior.
- Produces: current user-facing command documentation and recorded automated/read-only verification evidence; no live write.

- [ ] **Step 1: Update README command and safety documentation**

Document `training-sync sync YYYY-MM-DD [--yes]`, all-activity behavior, existing-daily requirement, shared confirmation, structured `type: 1`/`type: 2` cardio fields, full-day preservation, read-back verification, and retained-daily partial failures. Remove the obsolete statement that Weight x Reps receives a marker-only cycling row.

- [ ] **Step 2: Run focused feature tests**

Run: `python -m pytest tests/test_training_sync_cli.py tests/test_use_case_sync_day.py tests/test_garmin_daily_renderer.py tests/test_vault_training_block.py tests/test_weightxreps_text.py tests/test_weightxreps_jeditor.py tests/test_weightxreps_client.py tests/test_weightxreps_push.py -v`

Expected: PASS.

- [ ] **Step 3: Run the complete suite**

Run: `python -m pytest`

Expected: all tests PASS with no regressions.

- [ ] **Step 4: Run a read-only known-day preview**

Run: `training-sync garmin fetch 2026-07-03 && training-sync weightxreps preview 2026-07-03`

Expected: Garmin prints every known-day activity; preview emits valid structured rows without changing the vault or Weight x Reps. Do not run `training-sync sync` during this verification step.

- [ ] **Step 5: Review the final diff and commit documentation**

Run: `git diff --check && git status --short`

Expected: no whitespace errors and only intended feature/tests/README changes.

```bash
git add README.md
git commit -m "docs(sync): document multi-activity reconciliation"
```
