from training_sync.use_cases.weightxreps_preview import preview_weightxreps_day_from_vault


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
            "erows": [{"w": {"v": 0.0, "lb": 0, "usebw": 1}, "r": 5, "s": 3}],
        },
    ]
