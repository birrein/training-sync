import pytest

from training_sync.use_cases.weightxreps_preview import preview_weightxreps_day_from_vault
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
