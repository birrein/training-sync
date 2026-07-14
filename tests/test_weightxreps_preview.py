import pytest

from training_sync.domain.garmin_activity import GarminActivity
from training_sync.renderers.garmin_daily import render_training_activities
from training_sync.use_cases.weightxreps_preview import (
    load_weightxreps_day_from_vault,
    preview_weightxreps_day_from_vault,
)
from training_sync.weightxreps.exercise_resolution import ExerciseResolutionRequired


def test_preview_weightxreps_day_from_vault_builds_rows(tmp_path):
    vault = tmp_path / "vault"
    daily = vault / "daily/2026/06-June/2026-06-19-Friday.md"
    daily.parent.mkdir(parents=True)
    daily.write_text(
        """# Friday

## 🏃 Training
- Upper Body Day 2
```text
2026-06-19
@ 71.4 bw

#Chin Up
BW x 5, 5, 5
```

## 📚 Reading & Study
""",
        encoding="utf-8",
    )

    rows = preview_weightxreps_day_from_vault(
        vault,
        "2026-06-19",
        exercise_ids={"Chin Up": 10},
    )

    assert rows == [
        {"bw": 71.4, "lb": 0},
        {
            "on": "2026-06-19"
        },
        {
            "eid": 10,
            "erows": [{"w": {"v": 0.0, "lb": 0, "usebw": 1}, "r": 5, "s": 3, "type": 0}],
        },
    ]


def test_preview_weightxreps_day_from_vault_combines_ordered_text_blocks(tmp_path):
    vault = tmp_path / "vault"
    daily = vault / "daily/2026/06-June/2026-06-19-Friday.md"
    daily.parent.mkdir(parents=True)
    daily.write_text(
        """# Friday

## 🏃 Training
```text
2026-06-19
@ 71.4 bw

#Chin Up
BW x 5, 5, 5
```

- Morning Run
```text
2026-06-19

#Running
5.00km
@ Duration: 00:25:00.5
@ Avg HR: 148
```

- Evening Ride
```text
2026-06-19

#Cycling
27.95km
@ Duration: 01:00:20.0
@ Avg Power: 177
```
""",
        encoding="utf-8",
    )

    rows = preview_weightxreps_day_from_vault(
        vault,
        "2026-06-19",
        exercise_ids={"Chin Up": 10, "Running": 30, "Cycling": 40},
    )

    assert [row.get("eid") for row in rows if "eid" in row] == [10, 30, 40]
    assert rows[0] == {"bw": 71.4, "lb": 0}
    assert rows[-2]["erows"] == [
        {
            "type": 2,
            "t": 1_500_500,
            "d": {"val": 50_000_000, "unit": "km"},
            "c": "Avg HR: 148",
        }
    ]
    assert rows[-1]["erows"] == [
        {
            "type": 2,
            "t": 3_620_000,
            "d": {"val": 279_500_000, "unit": "km"},
            "c": "Avg Power: 177",
        }
    ]


def test_preview_weightxreps_day_normalizes_virtual_ride_to_cycling(tmp_path):
    vault = tmp_path / "vault"
    daily = vault / "daily/2026/07-July/2026-07-03-Friday.md"
    daily.parent.mkdir(parents=True)
    daily.write_text(
        """# Friday

## 🏃 Training
- Zwift Ride
```text
2026-07-03

#Virtual_ride
27.95km
@ Duration: 01:00:20.0
@ Avg HR: 148
```
""",
        encoding="utf-8",
    )

    rows = preview_weightxreps_day_from_vault(
        vault,
        "2026-07-03",
        exercise_ids={"Cycling": 40},
    )

    assert rows == [
        {"on": "2026-07-03"},
        {
            "eid": 40,
            "erows": [
                {
                    "type": 2,
                    "t": 3_620_000,
                    "d": {"val": 279_500_000, "unit": "km"},
                    "c": "Avg HR: 148",
                }
            ],
        },
    ]


def test_rendered_supported_aliases_round_trip_to_canonical_preview_rows_and_skip_strength(tmp_path):
    vault = tmp_path / "vault"
    daily = vault / "daily/2026/07-July/2026-07-03-Friday.md"
    daily.parent.mkdir(parents=True)
    aliases = [
        ("running", "Running", 30),
        ("trail_running", "Running", 30),
        ("treadmill_running", "Running", 30),
        ("virtual_run", "Running", 30),
        ("cycling", "Cycling", 40),
        ("virtual_ride", "Cycling", 40),
        ("ride", "Cycling", 40),
        ("indoor_cycling", "Cycling", 40),
        ("road_biking", "Cycling", 40),
        ("mountain_biking", "Cycling", 40),
        ("walking", "Walking", 50),
        ("swimming", "Swimming", 60),
        ("lap_swimming", "Swimming", 60),
        ("rowing", "Rowing", 70),
        ("indoor_rowing", "Rowing", 70),
        ("cardio", "Cardio", 80),
        ("generic_cardio", "Cardio", 80),
        ("strength_training", None, None),
    ]
    activities = [
        GarminActivity(
            activity_id=index,
            name=f"Activity {index}",
            start_time=f"2026-07-03 {index:02d}:00:00",
            type_key=type_key,
            duration_ms=1_800_000,
            distance_m=None if type_key == "strength_training" else 5_000,
        )
        for index, (type_key, _, _) in enumerate(aliases, start=1)
    ]
    rendered = render_training_activities("2026-07-03", activities)
    daily.write_text(
        f"# Friday\n\n## 🏃 Training\n{rendered}\n\n## 📚 Reading & Study\n",
        encoding="utf-8",
    )
    exercise_ids = {
        canonical_name: exercise_id
        for _, canonical_name, exercise_id in aliases
        if canonical_name is not None
    }

    loaded = load_weightxreps_day_from_vault(vault, "2026-07-03")
    rows = preview_weightxreps_day_from_vault(
        vault,
        "2026-07-03",
        exercise_ids=exercise_ids,
    )

    expected_names = [name for _, name, _ in aliases if name is not None]
    expected_ids = [exercise_id for _, name, exercise_id in aliases if name is not None]
    rendered_tags = [line.removeprefix("#") for line in rendered.splitlines() if line.startswith("#")]

    assert rendered_tags == [
        name if name is not None else "Strength_training"
        for _, name, _ in aliases
    ]
    assert [exercise.name for exercise in loaded.exercises] == expected_names
    assert [row.get("eid") for row in rows if "eid" in row] == expected_ids
    for row in rows[1:]:
        assert row["erows"][0]["type"] == 2
        assert row["erows"][0]["t"] == 1_800_000
        assert row["erows"][0]["d"] == {"val": 50_000_000, "unit": "km"}
    assert "#Strength_training" in rendered
    assert "@ Duration: 00:30:00.0" in rendered


def test_preview_weightxreps_day_requires_exercise_resolution_before_new_exercise(tmp_path):
    vault = tmp_path / "vault"
    daily = vault / "daily/2026/06-June/2026-06-19-Friday.md"
    daily.parent.mkdir(parents=True)
    daily.write_text(
        """# Friday

## 🏃 Training
```text
2026-06-19

#Barbell Hip Thrust with Bench
80kg x 10, 10, 10
```
""",
        encoding="utf-8",
    )

    with pytest.raises(ExerciseResolutionRequired) as exc:
        preview_weightxreps_day_from_vault(
            vault,
            "2026-06-19",
            exercise_ids={"Barbell Hip Thrust": 157721},
        )

    assert exc.value.payload()["catalog_source"] == "partial_jeditor"
