from __future__ import annotations

from copy import deepcopy
import json

import pytest

from training_sync.domain.planned_workout import planned_workout_from_dict
from training_sync.garmin.planned_workouts import project_planned_workout
from training_sync.use_cases.manage_planned_workouts import (
    RemotePermissionError,
    StaleBaselineError,
    UnsupportedRemoteStructureError,
    delete_workout,
    duplicate_workout,
    list_workouts,
    read_workout,
    update_workout,
)


def plan(name="Managed Plan", kg=83):
    return planned_workout_from_dict(
        {
            "schema_version": 1,
            "key": "managed-plan",
            "name": name,
            "sport": "strength_training",
            "exercises": [
                {
                    "name": "Romanian Deadlift",
                    "sets": [
                        {"reps": 10, "load": {"kind": "mass", "kg": kg, "basis": "total"}}
                    ],
                    "rest_between_sets": None,
                    "rest_after_exercise": {"until": "time", "seconds": 165},
                }
            ],
        }
    )


def grouped_plan(name="Managed Grouped Plan", kg=83):
    return planned_workout_from_dict(
        {
            "schema_version": 1,
            "key": "managed-grouped-plan",
            "name": name,
            "sport": "strength_training",
            "exercises": [
                {
                    "name": "Romanian Deadlift",
                    "sets": [
                        {"reps": 10, "load": {"kind": "mass", "kg": kg, "basis": "total"}},
                        {"reps": 10, "load": {"kind": "mass", "kg": kg, "basis": "total"}},
                    ],
                    "rest_between_sets": {"until": "time", "seconds": 165},
                    "rest_after_exercise": {"until": "time", "seconds": 165},
                }
            ],
        }
    )


class FakeManagementClient:
    def __init__(self, workouts=None):
        self.workouts = {int(key): deepcopy(value) for key, value in (workouts or {}).items()}
        for key, value in self.workouts.items():
            value["workoutId"] = key
        self.scheduled = {}
        self.update_calls = 0
        self.upload_calls = 0
        self.delete_calls = 0
        self.timeout_after_delete = False
        self.permission_denied = False
        self._next_id = max(self.workouts, default=100) + 1

    def get_workouts(self, start=0, limit=100):
        values = list(self.workouts.values())
        return deepcopy(values[start : start + limit])

    def get_workout_by_id(self, workout_id):
        if self.permission_denied:
            raise PermissionError("forbidden")
        if int(workout_id) not in self.workouts:
            raise KeyError(workout_id)
        return deepcopy(self.workouts[int(workout_id)])

    def update_workout(self, workout_id, payload):
        self.update_calls += 1
        self.workouts[int(workout_id)] = deepcopy(payload)
        self.workouts[int(workout_id)]["workoutId"] = int(workout_id)
        return {"workoutId": int(workout_id)}

    def upload_workout(self, payload):
        self.upload_calls += 1
        workout_id = self._next_id
        self._next_id += 1
        self.workouts[workout_id] = deepcopy(payload)
        self.workouts[workout_id]["workoutId"] = workout_id
        return {"workoutId": workout_id}

    def delete_workout(self, workout_id):
        self.delete_calls += 1
        self.workouts.pop(int(workout_id), None)
        if self.timeout_after_delete:
            raise TimeoutError("delete response timed out")

    def get_scheduled_workouts(self, year, month):
        return {
            "scheduledWorkouts": [
                deepcopy(item)
                for item in self.scheduled.values()
                if item["date"].startswith(f"{int(year):04d}-{int(month):02d}")
            ]
        }


def remote_plan(plan_name="Remote Plan"):
    payload = project_planned_workout(plan(plan_name)).payload
    payload["workoutId"] = 7
    payload["author"] = {"name": "manual owner"}
    payload["unrelatedMetadata"] = {"keep": True}
    return payload


def remote_grouped_plan(*, flat=False):
    payload = project_planned_workout(grouped_plan()).payload
    if flat:
        projection = project_planned_workout(grouped_plan())
        payload["workoutSegments"][0]["workoutSteps"] = [
            deepcopy(step) for step in projection.steps
        ]
    payload["workoutId"] = 7
    payload["author"] = {"name": "manual owner"}
    payload["unrelatedMetadata"] = {"keep": True}
    return payload


def test_inventory_is_bounded_paginated_and_includes_manual_workouts():
    client = FakeManagementClient(
        {
            1: remote_plan("One"),
            2: remote_plan("Two"),
            3: remote_plan("Three"),
            4: remote_plan("Four"),
        }
    )

    inventory = list_workouts(client, page_size=2, max_pages=2)

    assert [item["workoutId"] for item in inventory.items] == [1, 2, 3, 4]
    assert inventory.incomplete is True
    assert inventory.pages == 2


def test_read_uses_exact_id_and_surfaces_permission_failure():
    client = FakeManagementClient({42: remote_plan()})

    assert read_workout(client, 42)["workoutId"] == 42
    client.permission_denied = True
    with pytest.raises(RemotePermissionError):
        read_workout(client, 42)


def test_update_preserves_unrelated_remote_fields_and_verifies_template_scope():
    client = FakeManagementClient({7: remote_plan()})
    baseline = client.get_workout_by_id(7)

    result = update_workout(
        client,
        7,
        plan(kg=90),
        authorized=True,
        baseline=baseline,
        journal_path=None,
    )

    saved = client.workouts[7]
    assert result.state == "verified"
    assert result.workout_id == 7
    assert result.scope == "template"
    assert saved["author"] == {"name": "manual owner"}
    assert saved["unrelatedMetadata"] == {"keep": True}
    assert saved["workoutSegments"][0]["workoutSteps"][0]["weightValue"] == 90000


def test_update_converts_exact_flat_template_to_grouped_without_losing_metadata():
    client = FakeManagementClient({7: remote_grouped_plan(flat=True)})

    result = update_workout(
        client,
        7,
        grouped_plan(kg=90),
        authorized=True,
        journal_path=None,
    )

    saved = client.workouts[7]
    steps = saved["workoutSegments"][0]["workoutSteps"]
    assert result.state == "verified"
    assert result.workout_id == 7
    assert client.update_calls == 1
    assert steps[0]["type"] == "RepeatGroupDTO"
    assert steps[0]["numberOfIterations"] == 2
    assert steps[0]["workoutSteps"][0]["weightValue"] == 90000
    assert saved["author"] == {"name": "manual owner"}
    assert saved["unrelatedMetadata"] == {"keep": True}


def test_update_edits_grouped_load_and_preserves_group_and_metadata():
    client = FakeManagementClient({7: remote_grouped_plan()})

    result = update_workout(
        client,
        7,
        grouped_plan(kg=90),
        authorized=True,
        journal_path=None,
    )

    saved_group = client.workouts[7]["workoutSegments"][0]["workoutSteps"][0]
    assert result.state == "verified"
    assert saved_group["type"] == "RepeatGroupDTO"
    assert saved_group["numberOfIterations"] == 2
    assert saved_group["workoutSteps"][0]["weightValue"] == 90000
    assert client.workouts[7]["unrelatedMetadata"] == {"keep": True}


def test_grouped_duplicate_preserves_repeat_tree_and_unrelated_metadata():
    client = FakeManagementClient({7: remote_grouped_plan()})

    result = duplicate_workout(
        client,
        7,
        name="Grouped Copy",
        authorized=True,
        journal_path=None,
    )

    copied = client.workouts[result.workout_id]
    assert result.state == "verified"
    assert copied["workoutName"] == "Grouped Copy"
    assert copied["workoutSegments"][0]["workoutSteps"][0]["type"] == "RepeatGroupDTO"
    assert copied["author"] == {"name": "manual owner"}
    assert copied["unrelatedMetadata"] == {"keep": True}


def test_regrouping_rejects_conflicting_per_set_provider_metadata_before_mutation():
    remote = remote_grouped_plan(flat=True)
    physical_steps = remote["workoutSegments"][0]["workoutSteps"]
    physical_steps[0]["providerMetadata"] = {"source": "first"}
    physical_steps[2]["providerMetadata"] = {"source": "second"}
    client = FakeManagementClient({7: remote})

    with pytest.raises(UnsupportedRemoteStructureError, match="metadata"):
        update_workout(
            client,
            7,
            grouped_plan(kg=90),
            authorized=True,
            journal_path=None,
        )
    assert client.update_calls == 0


def test_update_rejects_unsupported_repeat_structure_without_mutation():
    remote = remote_plan()
    remote["workoutSegments"][0]["workoutSteps"] = [
        {
            "type": "RepeatGroupDTO",
            "stepOrder": 1,
            "numberOfIterations": 2,
            "workoutSteps": [],
        }
    ]
    client = FakeManagementClient({7: remote})

    with pytest.raises(UnsupportedRemoteStructureError):
        update_workout(
            client,
            7,
            plan(kg=90),
            authorized=True,
            journal_path=None,
        )
    assert client.update_calls == 0


def test_update_rejects_stale_baseline_before_remote_mutation():
    client = FakeManagementClient({7: remote_plan()})
    baseline = client.get_workout_by_id(7)
    client.workouts[7]["unrelatedMetadata"] = {"changed": True}

    with pytest.raises(StaleBaselineError):
        update_workout(
            client,
            7,
            plan(kg=90),
            authorized=True,
            baseline=baseline,
            journal_path=None,
        )
    assert client.update_calls == 0


def test_duplicate_creates_verified_new_template_without_touching_original():
    original = remote_plan()
    client = FakeManagementClient({7: original})

    result = duplicate_workout(
        client,
        7,
        name="Duplicated Plan",
        authorized=True,
        journal_path=None,
    )

    assert result.state == "verified"
    assert result.workout_id != 7
    assert client.workouts[7] == original
    assert client.workouts[result.workout_id]["workoutName"] == "Duplicated Plan"


def test_delete_requires_explicit_authorization_and_rejects_referenced_template():
    client = FakeManagementClient({7: remote_plan()})
    client.scheduled[900] = {"scheduleId": 900, "workoutId": 7, "date": "2026-09-13"}

    preview = delete_workout(client, 7, authorized=False, journal_path=None)
    assert preview.state == "preview"
    assert client.delete_calls == 0

    with pytest.raises(UnsupportedRemoteStructureError, match="scheduled"):
        delete_workout(client, 7, authorized=True, journal_path=None)
    assert client.delete_calls == 0


def test_delete_unreferenced_template_verifies_absence():
    client = FakeManagementClient({7: remote_plan()})

    result = delete_workout(client, 7, authorized=True, journal_path=None)

    assert result.state == "verified"
    assert result.workout_id == 7
    assert 7 not in client.workouts


def test_delete_reconciles_lost_response_by_reading_exact_template(tmp_path):
    client = FakeManagementClient({7: remote_plan()})
    client.timeout_after_delete = True

    result = delete_workout(
        client,
        7,
        authorized=True,
        journal_path=tmp_path / "journal.json",
    )

    assert result.state == "verified"
    assert result.workout_id == 7
    assert client.delete_calls == 1


def test_crud_mutations_record_operation_and_state_in_journal(tmp_path):
    client = FakeManagementClient({7: remote_plan()})
    journal_path = tmp_path / "journal.json"
    baseline = client.get_workout_by_id(7)

    update_workout(
        client,
        7,
        plan(kg=90),
        authorized=True,
        baseline=baseline,
        journal_path=journal_path,
        account="crud-account",
    )
    duplicated = duplicate_workout(
        client,
        7,
        name="Copy",
        authorized=True,
        journal_path=journal_path,
        account="crud-account",
    )
    delete_workout(
        client,
        duplicated.workout_id,
        authorized=True,
        journal_path=journal_path,
        account="crud-account",
    )

    entries = json.loads(journal_path.read_text(encoding="utf-8"))["entries"].values()
    assert {(entry["operation"], entry["state"]) for entry in entries} >= {
        ("update", "verified"),
        ("duplicate", "verified"),
        ("delete", "verified"),
    }
