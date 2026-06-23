from pathlib import Path

import pytest

from training_sync.use_cases.weightxreps_push import push_weightxreps_day


class FakeWeightxRepsClient:
    def __init__(self, existing=False, exercise_ids=None):
        self.existing = existing
        self.exercise_ids_map = exercise_ids or {}
        self.saved_rows = None

    def day_has_content(self, date):
        return self.existing

    def exercise_ids(self, date):
        return self.exercise_ids_map

    def save_jeditor(self, rows):
        self.saved_rows = rows
        return {"saveJEditor": True}

    def verify_day(self, date, rows):
        return True


def _write_daily(vault: Path):
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


def test_push_weightxreps_day_writes_rows_when_remote_day_is_empty(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=False)

    result = push_weightxreps_day(
        vault,
        "2026-06-19",
        client,
        exercise_ids={"Chin Up": 10},
        yes=False,
    )

    assert result == "saved"
    assert client.saved_rows[0] == {"bw": 71.4, "lb": 0}


def test_push_weightxreps_day_uses_remote_exercise_ids_when_not_provided(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=False, exercise_ids={"Chin Up": 10})

    push_weightxreps_day(
        vault,
        "2026-06-19",
        client,
        exercise_ids={},
        yes=False,
    )

    assert client.saved_rows[2]["eid"] == 10


def test_push_weightxreps_day_requires_yes_when_remote_day_exists(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=True)

    with pytest.raises(RuntimeError, match="already has content"):
        push_weightxreps_day(
            vault,
            "2026-06-19",
            client,
            exercise_ids={"Chin Up": 10},
            yes=False,
        )


def test_push_weightxreps_day_replaces_existing_day_with_yes(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=True)

    result = push_weightxreps_day(
        vault,
        "2026-06-19",
        client,
        exercise_ids={"Chin Up": 10},
        yes=True,
    )

    assert result == "replaced"
    assert client.saved_rows is not None
