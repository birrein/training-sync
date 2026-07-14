from pathlib import Path

import pytest

from training_sync.domain.garmin_activity import GarminActivity
from training_sync.renderers.weightxreps_text import ParsedExercise, ParsedSetLine, ParsedTrainingDay
from training_sync.use_cases.sync_day import (
    PartialSyncFailure,
    SyncDependencies,
    apply_sync_plan,
    build_complete_training_day,
    preflight_sync_day,
    sync_day,
)
from training_sync.weightxreps.client import VerificationMismatch
from training_sync.weightxreps.exercise_mapping import ExerciseMapping
from training_sync.weightxreps.exercise_resolution import ExerciseResolutionRequired


DATE = "2026-07-03"


def activity(activity_id: int, start: str, type_key: str = "running") -> dict:
    return {
        "activityId": activity_id,
        "activityName": f"Activity {activity_id}",
        "startTimeLocal": start,
        "activityType": {"typeKey": type_key},
        "duration": 1800.0,
        "distance": 5000.0,
    }


class FakeGarmin:
    def __init__(self, activities):
        self.activities = activities
        self.calls = []

    def get_activities_by_date(self, start, end):
        self.calls.append((start, end))
        return self.activities


class FakeWeightxReps:
    def __init__(
        self,
        *,
        existing=False,
        exercise_ids=None,
        save_error=None,
        verification_error=None,
    ):
        self.existing = existing
        self.exercise_ids_map = {"Running": 30, "Cycling": 40}
        self.exercise_ids_map.update(exercise_ids or {})
        self.calls = []
        self.writes = []
        self.save_error = save_error
        self.verification_error = verification_error

    def day_has_content(self, date):
        self.calls.append(("day_has_content", date))
        return self.existing

    def exercise_ids(self, date):
        self.calls.append(("exercise_ids", date))
        return self.exercise_ids_map

    def exercise_catalog(self, user_id):
        self.calls.append(("exercise_catalog", user_id))
        return self.exercise_ids_map

    def save_jeditor(self, rows):
        self.writes.append(("save", rows))
        if self.save_error is not None:
            raise self.save_error

    def verify_day(self, date, rows):
        self.writes.append(("verify", date, rows))
        if self.verification_error is not None:
            raise self.verification_error


def fake_dependencies(
    tmp_path: Path,
    *,
    activities,
    daily_content="",
    create_daily=True,
    existing_remote=False,
    exercise_ids=None,
    mappings=None,
    user_id=None,
    save_error=None,
    verification_error=None,
):
    vault = tmp_path / "vault"
    daily = vault / "daily/2026/07-July/2026-07-03-Friday.md"
    if create_daily:
        daily.parent.mkdir(parents=True)
        daily.write_text(
            f"# Friday\n\n## 🏃 Training\n{daily_content}\n\n## 📚 Reading & Study\n",
            encoding="utf-8",
        )
    garmin = FakeGarmin(activities)
    weightxreps = FakeWeightxReps(
        existing=existing_remote,
        exercise_ids=exercise_ids,
        save_error=save_error,
        verification_error=verification_error,
    )
    deps = SyncDependencies(
        garmin=garmin,
        weightxreps=weightxreps,
        vault_root=vault,
        mappings=mappings or [],
        user_id=user_id,
    )
    return deps, daily


def assert_no_writes(deps, daily, original=None):
    assert deps.weightxreps.writes == []
    if original is not None:
        assert daily.read_text(encoding="utf-8") == original


def test_garmin_activity_normalizes_required_and_optional_fields():
    normalized = GarminActivity.from_garmin(
        {
            **activity(10, "2026-07-03 07:00:00", "cycling"),
            "averageHR": "148",
            "maxHR": 171,
            "elevationGain": "158.5",
            "avgPower": 177.9,
            "calories": "530",
            "activityTrainingLoad": "84.2",
        }
    )

    assert normalized == GarminActivity(
        activity_id=10,
        name="Activity 10",
        start_time="2026-07-03 07:00:00",
        type_key="cycling",
        duration_ms=1_800_000,
        distance_m=5000.0,
        average_hr=148,
        max_hr=171,
        elevation_gain_m=158.5,
        average_power_w=177,
        calories=530,
        training_load=84.2,
    )


def test_garmin_activity_accepts_missing_optional_values():
    raw = activity(10, "2026-07-03 07:00:00")
    raw["distance"] = None

    normalized = GarminActivity.from_garmin(raw)

    assert normalized.distance_m is None
    assert normalized.average_hr is None
    assert normalized.max_hr is None
    assert normalized.elevation_gain_m is None
    assert normalized.average_power_w is None
    assert normalized.calories is None
    assert normalized.training_load is None


def test_preflight_orders_every_activity_and_does_not_write(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[
            activity(30, "2026-07-03 18:00:00"),
            activity(20, "2026-07-03 07:00:00"),
            activity(10, "2026-07-03 07:00:00"),
        ],
    )
    original = daily.read_text(encoding="utf-8")

    plan = preflight_sync_day(DATE, yes=True, deps=deps)

    assert [item.activity_id for item in plan.activities] == [10, 20, 30]
    assert deps.garmin.calls == [(DATE, DATE)]
    assert_no_writes(deps, daily, original)


@pytest.mark.parametrize("activity_count", [1, 2])
def test_preflight_accepts_one_or_multiple_activities_without_writing(tmp_path, activity_count):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(index, f"2026-07-03 0{index}:00:00") for index in range(1, activity_count + 1)],
    )
    original = daily.read_text(encoding="utf-8")

    plan = preflight_sync_day(DATE, yes=True, deps=deps)

    assert len(plan.activities) == activity_count
    assert_no_writes(deps, daily, original)


def test_preflight_rejects_zero_activities_without_writing(tmp_path):
    deps, daily = fake_dependencies(tmp_path, activities=[])
    original = daily.read_text(encoding="utf-8")

    with pytest.raises(RuntimeError, match="No Garmin activities"):
        preflight_sync_day(DATE, yes=True, deps=deps)

    assert_no_writes(deps, daily, original)


def test_preflight_rejects_missing_daily_without_writing(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
        create_daily=False,
    )

    with pytest.raises(FileNotFoundError, match="Daily note not found"):
        preflight_sync_day(DATE, yes=True, deps=deps)

    assert_no_writes(deps, daily)
    assert not daily.exists()


def test_preflight_rejects_missing_training_heading_without_writing(tmp_path):
    deps, daily = fake_dependencies(tmp_path, activities=[activity(1, "2026-07-03 07:00:00")])
    daily.write_text("# Friday\n\n## 📚 Reading & Study\n", encoding="utf-8")
    original = daily.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="Training section not found"):
        preflight_sync_day(DATE, yes=True, deps=deps)

    assert_no_writes(deps, daily, original)


def test_preflight_rejects_existing_daily_content_without_yes_and_does_not_write(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
        daily_content="Already logged",
    )
    original = daily.read_text(encoding="utf-8")

    with pytest.raises(RuntimeError, match="--yes"):
        preflight_sync_day(DATE, yes=False, deps=deps)

    assert_no_writes(deps, daily, original)


def test_preflight_preserves_strength_while_replacing_daily_cardio_in_memory_with_yes(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
        daily_content="""```text
2026-07-03

#Known Exercise
10kg x 5
```""",
        exercise_ids={"Known Exercise": 10},
    )
    original = daily.read_text(encoding="utf-8")

    plan = preflight_sync_day(DATE, yes=True, deps=deps)

    assert plan.original_daily == original
    assert plan.updated_daily != original
    assert plan.updated_daily.count("#Known Exercise") == 1
    assert "- Activity 1" in plan.updated_daily
    assert plan.updated_daily.count("## 🏃 Training") == 1
    assert_no_writes(deps, daily, original)


def test_apply_writes_updated_daily_once_before_weightxreps(monkeypatch, tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
    )
    plan = preflight_sync_day(DATE, yes=True, deps=deps)
    events = []
    original_write_text = Path.write_text

    def observed_write_text(path, data, *, encoding=None, errors=None, newline=None):
        events.append(("daily", path, encoding))
        return original_write_text(path, data, encoding=encoding, errors=errors, newline=newline)

    def observed_save(rows):
        events.append(("weightxreps", rows))

    monkeypatch.setattr(Path, "write_text", observed_write_text)
    monkeypatch.setattr(deps.weightxreps, "save_jeditor", observed_save)

    apply_sync_plan(plan, deps=deps)

    assert events == [
        ("daily", daily, "utf-8"),
        ("weightxreps", list(plan.weightxreps_rows)),
    ]
    assert daily.read_text(encoding="utf-8") == plan.updated_daily


def test_apply_returns_verified_result_after_matching_remote_readback(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
    )
    plan = preflight_sync_day(DATE, yes=True, deps=deps)

    result = apply_sync_plan(plan, deps=deps)

    assert result.weightxreps_verified is True
    assert deps.weightxreps.writes == [
        ("save", list(plan.weightxreps_rows)),
        ("verify", DATE, list(plan.weightxreps_rows)),
    ]
    assert daily.read_text(encoding="utf-8") == plan.updated_daily


def test_apply_wraps_save_error_after_preserving_written_daily(tmp_path):
    cause = RuntimeError("remote save unavailable")
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
        save_error=cause,
    )
    plan = preflight_sync_day(DATE, yes=True, deps=deps)

    with pytest.raises(PartialSyncFailure) as exc:
        apply_sync_plan(plan, deps=deps)

    assert exc.value.date == DATE
    assert exc.value.daily_path == daily
    assert exc.value.cause is cause
    assert DATE in str(exc.value)
    assert str(daily) in str(exc.value)
    assert "remote save unavailable" in str(exc.value)
    assert daily.read_text(encoding="utf-8") == plan.updated_daily


def test_apply_wraps_verification_mismatch_with_details_and_preserves_daily(tmp_path):
    mismatch = VerificationMismatch(
        expected=[
            {
                "eid": 30,
                "sets": [
                    {"type": 2, "t": 1_800_000, "d": 50_000_000, "dunit": "km"}
                ],
            }
        ],
        observed=[
            {
                "eid": 30,
                "sets": [
                    {"type": 2, "t": 1_800_000, "d": 50_000_000, "dunit": "mi"}
                ],
            }
        ],
    )
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
        verification_error=mismatch,
    )
    plan = preflight_sync_day(DATE, yes=True, deps=deps)

    with pytest.raises(PartialSyncFailure) as exc:
        apply_sync_plan(plan, deps=deps)

    assert exc.value.cause is mismatch
    assert "expected=" in str(exc.value)
    assert "observed=" in str(exc.value)
    assert daily.read_text(encoding="utf-8") == plan.updated_daily


def test_apply_retry_saves_identical_rows_after_partial_failure(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[
            activity(20, "2026-07-03 18:00:00", "cycling"),
            activity(10, "2026-07-03 07:00:00", "running"),
        ],
        daily_content="""```text
2026-07-03

#Barbell Row
51kg x 12, 12, 12

#Running
2.50km
@ Duration: 00:15:00.0
@ Avg HR: 120
```""",
        exercise_ids={"Barbell Row": 20, "Running": 30, "Cycling": 40},
        save_error=RuntimeError("first save failed"),
    )

    plan = preflight_sync_day(DATE, yes=True, deps=deps)

    with pytest.raises(PartialSyncFailure):
        apply_sync_plan(plan, deps=deps)
    first_rows = deps.weightxreps.writes[0][1]
    deps.weightxreps.save_error = None

    result = apply_sync_plan(plan, deps=deps)
    second_rows = deps.weightxreps.writes[1][1]

    assert first_rows == second_rows
    assert result.weightxreps_verified is True
    assert daily.read_text(encoding="utf-8").count("## 🏃 Training") == 1


def test_sync_day_retry_rebuilds_identical_full_day_from_retained_daily(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[
            activity(20, "2026-07-03 18:00:00", "cycling"),
            activity(10, "2026-07-03 07:00:00", "running"),
        ],
        daily_content="""```text
2026-07-03
@ 71.4 bw

#Barbell Row
51kg x 12, 12, 12

#Running
2.50km
@ Duration: 00:15:00.0
@ Avg HR: 120
```""",
        exercise_ids={"Barbell Row": 20, "Running": 30, "Cycling": 40},
        save_error=RuntimeError("first save failed"),
    )

    with pytest.raises(PartialSyncFailure):
        sync_day(DATE, yes=True, deps=deps)
    first_rows = deps.weightxreps.writes[0][1]
    retained_daily = daily.read_text(encoding="utf-8")
    deps.weightxreps.save_error = None

    result = sync_day(DATE, yes=True, deps=deps)
    second_rows = deps.weightxreps.writes[1][1]

    assert first_rows[0] == {"bw": 71.4, "lb": 0}
    assert [row.get("eid") for row in first_rows if "eid" in row] == [20, 30, 40]
    assert second_rows == first_rows
    assert result.weightxreps_verified is True
    assert "@ 71.4 bw" in retained_daily
    assert "#Barbell Row" in retained_daily
    assert "2.50km" not in retained_daily
    assert "@ Avg HR: 120" not in retained_daily
    assert retained_daily.count("- Activity 10") == 1
    assert retained_daily.count("- Activity 20") == 1
    assert daily.read_text(encoding="utf-8") == retained_daily


def test_sync_day_directly_runs_preflight_apply_and_verification(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
    )

    result = sync_day(DATE, yes=True, deps=deps)

    assert result.daily_path == daily
    assert result.activity_count == 1
    assert result.weightxreps_verified is True
    assert [write[0] for write in deps.weightxreps.writes] == ["save", "verify"]


def test_preflight_rejects_existing_remote_content_without_yes_and_does_not_write(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
        existing_remote=True,
    )
    original = daily.read_text(encoding="utf-8")

    with pytest.raises(RuntimeError, match="--yes"):
        preflight_sync_day(DATE, yes=False, deps=deps)

    assert_no_writes(deps, daily, original)


def test_preflight_rejects_unresolved_exercises_without_writing(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
        daily_content="""```text
2026-07-03

#Unknown Exercise
10kg x 5
```""",
        exercise_ids={"Known Exercise": 10},
        mappings=[
            ExerciseMapping(
                weightxreps_name="Different Exercise",
                weightxreps_id=20,
                aliases=["Different Exercise"],
            )
        ],
    )
    original = daily.read_text(encoding="utf-8")

    with pytest.raises(ExerciseResolutionRequired):
        preflight_sync_day(DATE, yes=True, deps=deps)

    assert_no_writes(deps, daily, original)


def test_preflight_rejects_exercises_that_would_be_created_without_writing(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(1, "2026-07-03 07:00:00")],
        mappings=[
            ExerciseMapping(
                weightxreps_name="Running",
                weightxreps_id=None,
                aliases=["Running"],
                create_if_missing=True,
            )
        ],
        user_id=123,
    )
    deps.weightxreps.exercise_ids_map = {}
    original = daily.read_text(encoding="utf-8")

    with pytest.raises(RuntimeError, match="cannot create Weight x Reps exercises: Running"):
        preflight_sync_day(DATE, yes=True, deps=deps)

    assert_no_writes(deps, daily, original)


def test_preflight_preserves_strength_and_builds_one_structured_block_per_cardio_activity(tmp_path):
    running = activity(10, "2026-07-03 07:00:00", "running")
    running.update({"activityName": "Morning Run", "averageHR": 148})
    cycling = activity(20, "2026-07-03 18:00:00", "cycling")
    cycling.update({"activityName": "Zwift Ride", "elevationGain": 158})
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[cycling, running],
        daily_content="""```text
2026-07-03
@ 71.4 bw

#Chin Up
BW x 5, 5, 5

#Barbell Row
51kg x 12, 12, 12
```""",
        exercise_ids={"Chin Up": 10, "Barbell Row": 20, "Running": 30, "Cycling": 40},
    )
    original = daily.read_text(encoding="utf-8")

    plan = preflight_sync_day(DATE, yes=True, deps=deps)

    assert plan.weightxreps_rows == (
        {"bw": 71.4, "lb": 0},
        {"on": DATE},
        {
            "eid": 10,
            "erows": [{"w": {"v": 0.0, "lb": 0, "usebw": 1}, "r": 5, "s": 3, "type": 0}],
        },
        {
            "eid": 20,
            "erows": [{"w": {"v": 51.0, "lb": 0}, "r": 12, "s": 3, "type": 0}],
        },
        {
            "eid": 30,
            "erows": [
                {
                    "type": 2,
                    "t": 1_800_000,
                    "d": {"val": 50_000_000, "unit": "km"},
                    "c": "Morning Run | Avg HR: 148",
                }
            ],
        },
        {
            "eid": 40,
            "erows": [
                {
                    "type": 2,
                    "t": 1_800_000,
                    "d": {"val": 50_000_000, "unit": "km"},
                    "c": "Zwift Ride | Elev Gain: 158 m",
                }
            ],
        },
    )
    assert daily.read_text(encoding="utf-8") == original


def test_preflight_builds_equal_weightxreps_rows_on_deterministic_retry(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[
            activity(20, "2026-07-03 18:00:00", "cycling"),
            activity(10, "2026-07-03 07:00:00", "running"),
        ],
        daily_content="""```text
2026-07-03

#Barbell Row
51kg x 12, 12, 12
```""",
        exercise_ids={"Barbell Row": 20, "Running": 30, "Cycling": 40},
    )
    original = daily.read_text(encoding="utf-8")

    first = preflight_sync_day(DATE, yes=True, deps=deps)
    second = preflight_sync_day(DATE, yes=True, deps=deps)

    assert first.weightxreps_rows == second.weightxreps_rows
    assert daily.read_text(encoding="utf-8") == original


def test_build_complete_training_day_preserves_only_strength_from_prior_day():
    strength = ParsedExercise(
        name="Barbell Row",
        sets=[ParsedSetLine(weight_kg=51.0, reps=(12, 12, 12))],
    )
    prior_cardio = ParsedExercise(
        name="Running",
        sets=[ParsedSetLine(set_type=2, duration_ms=900_000, distance=2.5, distance_unit="km")],
    )
    preserved = ParsedTrainingDay(
        date=DATE,
        body_weight_kg=71.4,
        exercises=[strength, prior_cardio],
    )
    garmin_activity = GarminActivity.from_garmin(activity(10, "2026-07-03 07:00:00"))

    complete = build_complete_training_day(DATE, preserved, [garmin_activity])

    assert complete.exercises[0] == strength
    assert len(complete.exercises) == 2
    assert complete.exercises[1].name == "Running"
    assert complete.exercises[1].sets[0].duration_ms == 1_800_000


def test_build_complete_training_day_maps_virtual_ride_to_cycling():
    raw = activity(20, "2026-07-03 18:00:00", "virtual_ride")
    virtual_ride = GarminActivity.from_garmin(raw)
    preserved = ParsedTrainingDay(date=DATE, body_weight_kg=None)

    complete = build_complete_training_day(DATE, preserved, [virtual_ride])

    assert complete.exercises[0].name == "Cycling"


def test_build_complete_training_day_ignores_non_cardio_activities_and_preserves_strength():
    strength = ParsedExercise(
        name="Barbell Row",
        sets=[ParsedSetLine(weight_kg=51.0, reps=(12, 12, 12))],
    )
    preserved = ParsedTrainingDay(
        date=DATE,
        body_weight_kg=71.4,
        exercises=[strength],
    )
    strength_activity = GarminActivity.from_garmin(
        activity(10, "2026-07-03 07:00:00", "strength_training")
    )
    running_activity = GarminActivity.from_garmin(
        activity(20, "2026-07-03 18:00:00", "running")
    )

    complete = build_complete_training_day(
        DATE,
        preserved,
        [strength_activity, running_activity],
    )

    assert complete.exercises[0] == strength
    assert [exercise.name for exercise in complete.exercises] == ["Barbell Row", "Running"]


def test_preflight_renders_non_cardio_activity_without_planning_weightxreps_cardio(tmp_path):
    deps, daily = fake_dependencies(
        tmp_path,
        activities=[activity(10, "2026-07-03 07:00:00", "strength_training")],
        user_id=123,
    )
    deps.weightxreps.exercise_ids_map = {}
    original = daily.read_text(encoding="utf-8")

    plan = preflight_sync_day(DATE, yes=True, deps=deps)

    assert "#Strength_training" in plan.updated_daily
    assert plan.weightxreps_rows == ({"on": DATE},)
    assert_no_writes(deps, daily, original)
