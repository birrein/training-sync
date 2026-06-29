from pathlib import Path

import pytest

from training_sync.use_cases.weightxreps_push import push_weightxreps_day
from training_sync.weightxreps.exercise_mapping import ExerciseMapping
from training_sync.weightxreps.exercise_resolution import ExerciseResolutionRequired


class FakeWeightxRepsClient:
    def __init__(self, existing=False, exercise_ids=None, exercise_catalog=None):
        self.existing = existing
        self.exercise_ids_map = exercise_ids or {}
        self.exercise_catalog_map = exercise_catalog or {}
        self.exercise_id_calls = []
        self.exercise_catalog_calls = []
        self.saved_rows = None

    def day_has_content(self, date):
        return self.existing

    def exercise_ids(self, date):
        self.exercise_id_calls.append(date)
        return self.exercise_ids_map

    def exercise_catalog(self, user_id):
        self.exercise_catalog_calls.append(user_id)
        return self.exercise_catalog_map

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


def test_push_weightxreps_day_uses_remote_exercise_catalog_when_user_id_is_provided(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=False, exercise_catalog={"Chin Up": 10})

    push_weightxreps_day(
        vault,
        "2026-06-19",
        client,
        exercise_ids={},
        yes=False,
        user_id=12345,
    )

    assert client.saved_rows[2]["eid"] == 10
    assert client.exercise_catalog_calls == [12345]
    assert client.exercise_id_calls == []


def test_push_weightxreps_day_treats_empty_user_catalog_as_authoritative(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(
        existing=False,
        exercise_ids={"Chin Up": 10},
        exercise_catalog={},
    )

    with pytest.raises(ExerciseResolutionRequired) as exc:
        push_weightxreps_day(
            vault,
            "2026-06-19",
            client,
            exercise_ids={},
            yes=False,
            user_id=12345,
        )

    assert exc.value.payload()["catalog_source"] == "full_catalog"
    assert client.exercise_catalog_calls == [12345]
    assert client.exercise_id_calls == []
    assert client.saved_rows is None


def test_push_weightxreps_day_reports_explicit_catalog_source_for_explicit_ids(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=False)

    with pytest.raises(ExerciseResolutionRequired) as exc:
        push_weightxreps_day(
            vault,
            "2026-06-19",
            client,
            exercise_ids={"Bench Press": 10},
            yes=False,
        )

    assert exc.value.payload()["catalog_source"] == "explicit"
    assert client.exercise_catalog_calls == []
    assert client.exercise_id_calls == []
    assert client.saved_rows is None


def test_push_weightxreps_day_prefers_explicit_exercise_ids_over_catalog(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=False, exercise_catalog={"Chin Up": 99})

    push_weightxreps_day(
        vault,
        "2026-06-19",
        client,
        exercise_ids={"Chin Up": 10},
        yes=False,
        user_id=12345,
    )

    assert client.saved_rows[2]["eid"] == 10
    assert client.exercise_catalog_calls == []
    assert client.exercise_id_calls == []


def test_push_weightxreps_day_creates_explicitly_mapped_new_exercise(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=False, exercise_catalog={})

    result = push_weightxreps_day(
        vault,
        "2026-06-19",
        client,
        exercise_ids={},
        yes=False,
        exercise_mappings=[
            ExerciseMapping(
                weightxreps_name="Chin Up",
                weightxreps_id=None,
                aliases=["Chin Up"],
                create_if_missing=True,
            )
        ],
        user_id=12345,
    )

    assert result == "saved"
    assert client.exercise_catalog_calls == [12345]
    assert client.exercise_id_calls == []
    assert client.saved_rows[1:3] == [
        {
            "on": "2026-06-19"
        },
        {"newExercise": "Chin Up"},
    ]


def test_push_weightxreps_day_does_not_create_with_partial_jeditor_catalog(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=False)

    with pytest.raises(ExerciseResolutionRequired) as exc:
        push_weightxreps_day(
            vault,
            "2026-06-19",
            client,
            exercise_ids={},
            yes=False,
            exercise_mappings=[
                ExerciseMapping(
                    weightxreps_name="Chin Up",
                    weightxreps_id=None,
                    aliases=["Chin Up"],
                    create_if_missing=True,
                )
            ],
        )

    payload = exc.value.payload()
    assert payload["catalog_source"] == "partial_jeditor"
    assert payload["unresolved"][0]["reason"] == "create_requires_full_catalog"
    assert client.saved_rows is None


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


def test_push_weightxreps_day_does_not_write_unresolved_exercises(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=False)

    with pytest.raises(ExerciseResolutionRequired) as exc:
        push_weightxreps_day(
            vault,
            "2026-06-19",
            client,
            exercise_ids={},
            yes=False,
        )

    assert exc.value.payload()["catalog_source"] == "partial_jeditor"
    assert client.saved_rows is None
