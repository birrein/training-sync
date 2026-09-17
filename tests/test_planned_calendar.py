from __future__ import annotations

from copy import deepcopy
import json

import pytest

from training_sync.domain.planned_workout import planned_workout_from_dict
from training_sync.garmin.planned_workouts import project_planned_workout
from training_sync.use_cases.manage_planned_workouts import (
    CalendarOperationError,
    list_calendar,
    move_calendar_workout,
    remove_calendar_workout,
    replace_calendar_workout,
    schedule_calendar_workout,
)


def plan(name="Calendar Plan", kg=83, rest=False):
    return planned_workout_from_dict(
        {
            "schema_version": 1,
            "key": f"calendar-{name.lower().replace(' ', '-')}",
            "name": name,
            "sport": "strength_training",
            "exercises": [
                {
                    "name": "Romanian Deadlift",
                    "sets": [{"reps": 10, "load": {"kind": "mass", "kg": kg, "basis": "total"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": {"until": "time", "seconds": 30} if rest else None,
                }
            ],
        }
    )


class FakeCalendarClient:
    def __init__(self, workout_id=7):
        payload = project_planned_workout(plan()).payload
        payload["workoutId"] = workout_id
        self.workouts = {workout_id: payload}
        self.scheduled = {}
        self.next_workout_id = 100
        self.next_schedule_id = 900
        self.schedule_calls = 0
        self.unschedule_calls = 0
        self.upload_calls = 0
        self.fail_upload = False
        self.fail_schedule = False
        self.bad_schedule_date = False
        self.fail_unschedule = False
        self.timeout_after_unschedule = False
        self.drop_rest_on_read = False
        self.fail_read_after_unschedule = False

    def get_workout_by_id(self, workout_id):
        value = deepcopy(self.workouts[int(workout_id)])
        if self.drop_rest_on_read:
            segments = value["workoutSegments"]
            segments[0]["workoutSteps"] = [
                step
                for step in segments[0]["workoutSteps"]
                if step["stepType"]["stepTypeKey"] != "rest"
            ]
        return value

    def get_workouts(self, start=0, limit=100):
        return deepcopy(list(self.workouts.values())[start : start + limit])

    def upload_workout(self, payload):
        self.upload_calls += 1
        if self.fail_upload:
            raise RuntimeError("create failed")
        workout_id = self.next_workout_id
        self.next_workout_id += 1
        stored = deepcopy(payload)
        stored["workoutId"] = workout_id
        self.workouts[workout_id] = stored
        return {"workoutId": workout_id}

    def schedule_workout(self, workout_id, date):
        self.schedule_calls += 1
        if self.fail_schedule:
            raise RuntimeError("schedule failed")
        schedule_id = self.next_schedule_id
        self.next_schedule_id += 1
        self.scheduled[schedule_id] = {
            "scheduleId": schedule_id,
            "workoutId": int(workout_id),
            "date": "2026-09-14" if self.bad_schedule_date else date,
        }
        return {"scheduleId": schedule_id}

    def get_scheduled_workout_by_id(self, schedule_id):
        if int(schedule_id) not in self.scheduled:
            if self.fail_read_after_unschedule:
                raise RuntimeError("calendar read temporarily unavailable")
            raise KeyError(schedule_id)
        return deepcopy(self.scheduled[int(schedule_id)])

    def get_scheduled_workouts(self, year, month):
        prefix = f"{int(year):04d}-{int(month):02d}"
        return {
            "scheduledWorkouts": [
                deepcopy(value)
                for value in self.scheduled.values()
                if value["date"].startswith(prefix)
            ]
        }

    def unschedule_workout(self, schedule_id):
        self.unschedule_calls += 1
        if self.fail_unschedule:
            raise RuntimeError("remove failed")
        self.scheduled.pop(int(schedule_id), None)
        if self.timeout_after_unschedule:
            raise TimeoutError("remove response timed out")


class ProviderBoundaryCalendarClient(FakeCalendarClient):
    def upload_workout(self, payload):
        assert payload["sportType"]["displayOrder"] == 4
        for segment in payload["workoutSegments"]:
            assert segment["sportType"]["displayOrder"] == 4
            for step in segment["workoutSteps"]:
                for field in (
                    "originalExerciseName",
                    "garminName",
                    "repetitionCount",
                    "weightBasis",
                    "loadKind",
                    "side",
                ):
                    assert field not in step
                if step.get("weightValue") is not None:
                    assert step["weightUnit"] == {
                        "unitId": 8,
                        "unitKey": "kilogram",
                        "factor": 1000.0,
                    }
                assert step.get("preferredEndConditionUnit") is None
        return super().upload_workout(payload)


class ScheduleHttp500Error(RuntimeError):
    status_code = 500

    def __str__(self):
        return (
            "API Error 500 {'errorId': 'calendar-ref-500', "
            "'error': 'MismatchedInputException', "
            "'authorization': 'Bearer calendar-secret'}"
        )


def schedule_existing(client, schedule_id, date, workout_id=7):
    client.scheduled[schedule_id] = {
        "scheduleId": schedule_id,
        "workoutId": workout_id,
        "date": date,
    }
    client.next_schedule_id = max(client.next_schedule_id, schedule_id + 1)


def test_calendar_list_preserves_local_dates_and_multiple_occurrences():
    client = FakeCalendarClient()
    schedule_existing(client, 900, "2026-09-13")
    schedule_existing(client, 901, "2026-09-13")

    inventory = list_calendar(client, "2026-09-13", "2026-09-13")

    assert [item["scheduleId"] for item in inventory.items] == [900, 901]
    assert all(item["date"] == "2026-09-13" for item in inventory.items)


def test_schedule_retry_reuses_exact_existing_occurrence():
    client = FakeCalendarClient()
    schedule_existing(client, 900, "2026-09-13")

    result = schedule_calendar_workout(
        client,
        7,
        "2026-09-13",
        authorized=True,
        journal_path=None,
    )

    assert result.state == "verified"
    assert result.schedule_id == 900
    assert result.reused is True
    assert client.schedule_calls == 0


def test_move_adds_and_verifies_destination_then_removes_only_original():
    client = FakeCalendarClient()
    schedule_existing(client, 900, "2026-09-13")
    schedule_existing(client, 901, "2026-09-20")
    original_template = deepcopy(client.workouts[7])

    result = move_calendar_workout(
        client,
        900,
        "2026-09-14",
        authorized=True,
        journal_path=None,
    )

    assert result.state == "verified"
    assert result.original_schedule_id == 900
    assert result.replacement_schedule_id != 900
    assert 900 not in client.scheduled
    assert client.scheduled[901]["date"] == "2026-09-20"
    assert client.workouts[7] == original_template


def test_remove_deletes_only_occurrence_and_preserves_template():
    client = FakeCalendarClient()
    schedule_existing(client, 900, "2026-09-13")
    original_template = deepcopy(client.workouts[7])

    result = remove_calendar_workout(
        client,
        900,
        authorized=True,
        journal_path=None,
    )

    assert result.state == "verified"
    assert 900 not in client.scheduled
    assert client.workouts[7] == original_template


def test_successful_calendar_mutation_records_atomic_local_state(tmp_path):
    client = FakeCalendarClient()
    journal_path = tmp_path / "journal.json"

    result = schedule_calendar_workout(
        client,
        7,
        "2026-09-13",
        authorized=True,
        journal_path=journal_path,
        account="calendar-account",
    )

    document = json.loads(journal_path.read_text(encoding="utf-8"))
    entries = list(document["entries"].values())
    assert result.state == "verified"
    assert len(entries) == 1
    assert entries[0]["state"] == "scheduled"
    assert entries[0]["schedule_id"] == result.schedule_id
    assert all("source" not in entry for entry in entries)


def test_calendar_schedule_failure_returns_safe_diagnostics(tmp_path):
    class FailingScheduleClient(FakeCalendarClient):
        def schedule_workout(self, workout_id, date):
            self.schedule_calls += 1
            raise ScheduleHttp500Error()

    client = FailingScheduleClient()
    result = schedule_calendar_workout(
        client,
        7,
        "2026-09-13",
        authorized=True,
        journal_path=tmp_path / "journal.json",
    )

    assert result.state == "uncertain"
    assert result.diagnostics == {
        "stage": "schedule",
        "http_status": 500,
        "provider_error_type": "MismatchedInputException",
        "reference_id": "calendar-ref-500",
    }
    assert "calendar-secret" not in (result.error or "")


def test_remove_does_not_claim_absence_when_post_delete_readback_is_unavailable():
    client = FakeCalendarClient()
    schedule_existing(client, 900, "2026-09-13")
    client.fail_read_after_unschedule = True

    result = remove_calendar_workout(
        client,
        900,
        authorized=True,
        journal_path=None,
    )

    assert result.state == "uncertain"
    assert "read" in result.error


def test_remove_retry_reconciles_a_lost_delete_response_without_repeating_delete(tmp_path):
    client = FakeCalendarClient()
    schedule_existing(client, 900, "2026-09-13")
    client.timeout_after_unschedule = True
    journal_path = tmp_path / "journal.json"

    first = remove_calendar_workout(
        client,
        900,
        authorized=True,
        journal_path=journal_path,
    )
    client.timeout_after_unschedule = False
    second = remove_calendar_workout(
        client,
        900,
        authorized=True,
        journal_path=journal_path,
    )

    assert first.state == "uncertain"
    assert second.state == "verified"
    assert client.unschedule_calls == 1


def test_replace_clones_one_date_and_keeps_other_occurrences_and_template():
    client = ProviderBoundaryCalendarClient()
    schedule_existing(client, 900, "2026-09-13")
    schedule_existing(client, 901, "2026-09-20")
    original_template = deepcopy(client.workouts[7])

    result = replace_calendar_workout(
        client,
        900,
        plan(name="Changed Calendar Plan", kg=90),
        authorized=True,
        journal_path=None,
    )

    assert result.state == "verified"
    assert result.original_schedule_id == 900
    assert result.replacement_workout_id != 7
    assert result.replacement_schedule_id in client.scheduled
    assert 900 not in client.scheduled
    assert client.scheduled[901]["workoutId"] == 7
    assert client.workouts[7] == original_template
    assert client.workouts[result.replacement_workout_id]["workoutSegments"][0]["workoutSteps"][0]["weightValue"] == 90
    assert client.workouts[result.replacement_workout_id]["workoutSegments"][0]["workoutSteps"][0]["weightUnit"] == {
        "unitId": 8,
        "unitKey": "kilogram",
        "factor": 1000.0,
    }


def test_replace_retry_reuses_existing_variant_after_original_removal_failure(tmp_path):
    client = FakeCalendarClient()
    schedule_existing(client, 900, "2026-09-13")
    journal_path = tmp_path / "journal.json"
    client.fail_unschedule = True

    first = replace_calendar_workout(
        client,
        900,
        plan(name="Replacement", kg=90),
        authorized=True,
        journal_path=journal_path,
    )
    client.fail_unschedule = False
    second = replace_calendar_workout(
        client,
        900,
        plan(name="Replacement", kg=90),
        authorized=True,
        journal_path=journal_path,
    )

    assert first.state == "partial"
    assert second.state == "verified"
    assert second.replacement_workout_id == first.replacement_workout_id
    assert client.upload_calls == 1
    assert 900 not in client.scheduled


@pytest.mark.parametrize(
    ("failure", "expected_state"),
    [
        ("create", "uncertain"),
        ("verify", "partial"),
        ("schedule", "partial"),
        ("schedule_verify", "partial"),
        ("remove", "partial"),
    ],
)
def test_replace_exposes_each_partial_boundary_without_erasing_original(
    failure, expected_state
):
    client = FakeCalendarClient()
    schedule_existing(client, 900, "2026-09-13")
    if failure == "create":
        client.fail_upload = True
    elif failure == "verify":
        client.drop_rest_on_read = True
    elif failure == "schedule":
        client.fail_schedule = True
    elif failure == "schedule_verify":
        client.bad_schedule_date = True
    elif failure == "remove":
        client.fail_unschedule = True

    replacement_plan = plan(
        name="Replacement",
        kg=90,
        rest=(failure == "verify"),
    )
    result = replace_calendar_workout(
        client,
        900,
        replacement_plan,
        authorized=True,
        journal_path=None,
    )

    assert result.state == expected_state
    assert 900 in client.scheduled
    assert result.original_schedule_id == 900
