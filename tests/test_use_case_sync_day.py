from pathlib import Path

import pytest

from training_sync.domain.garmin_activity import GarminActivity
from training_sync.use_cases.sync_day import SyncDependencies, preflight_sync_day
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
    def __init__(self, *, existing=False, exercise_ids=None):
        self.existing = existing
        self.exercise_ids_map = exercise_ids or {}
        self.calls = []
        self.writes = []

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

    def verify_day(self, date, rows):
        self.writes.append(("verify", date, rows))
        return True


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
    weightxreps = FakeWeightxReps(existing=existing_remote, exercise_ids=exercise_ids)
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
