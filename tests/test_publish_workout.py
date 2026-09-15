from __future__ import annotations

from copy import deepcopy
from threading import Lock
import time

import pytest

from training_sync.domain.planned_workout import planned_workout_from_dict
from training_sync.use_cases.publish_workout import (
    PublicationConflictError,
    publish_workout,
)


def strength_plan(*, date=None):
    plan = {
        "schema_version": 1,
        "key": "publishable-plan",
        "name": "Publishable Plan",
        "sport": "strength_training",
        "exercises": [
            {
                "name": "Romanian Deadlift",
                "sets": [
                    {"reps": 10, "load": {"kind": "mass", "kg": 83, "basis": "total"}},
                    {"reps": 8, "load": {"kind": "mass", "kg": 85, "basis": "total"}},
                ],
                "rest_between_sets": {"until": "time", "seconds": 165},
                "rest_after_exercise": {"until": "time", "seconds": 165},
            }
        ],
    }
    if date is not None:
        plan["date"] = date
    return planned_workout_from_dict(plan)


class FakeGarminClient:
    def __init__(self):
        self.workouts = {}
        self.scheduled = {}
        self.upload_calls = 0
        self.schedule_calls = 0
        self.fail_schedule = False
        self.timeout_after_upload = False
        self.duplicate_on_timeout = False
        self.drop_rest_on_read = False
        self.delay_upload = 0
        self._next_workout_id = 100
        self._next_schedule_id = 900
        self._lock = Lock()

    def upload_workout(self, payload):
        if self.delay_upload:
            time.sleep(self.delay_upload)
        with self._lock:
            self.upload_calls += 1
            workout_id = self._next_workout_id
            self._next_workout_id += 1
            stored = deepcopy(payload)
            stored["workoutId"] = workout_id
            self.workouts[workout_id] = stored
            if self.timeout_after_upload:
                if self.duplicate_on_timeout:
                    duplicate_id = self._next_workout_id
                    self._next_workout_id += 1
                    duplicate = deepcopy(stored)
                    duplicate["workoutId"] = duplicate_id
                    self.workouts[duplicate_id] = duplicate
                raise TimeoutError("upload response timed out")
            return {"workoutId": workout_id}

    def get_workout_by_id(self, workout_id):
        result = deepcopy(self.workouts[int(workout_id)])
        if self.drop_rest_on_read:
            steps = result["workoutSegments"][0]["workoutSteps"]
            result["workoutSegments"][0]["workoutSteps"] = [
                step for step in steps if step["stepType"]["stepTypeKey"] != "rest"
            ]
        return result

    def get_workouts(self, start=0, limit=100):
        values = list(self.workouts.values())
        return deepcopy(values[start : start + limit])

    def schedule_workout(self, workout_id, date):
        self.schedule_calls += 1
        if self.fail_schedule:
            raise RuntimeError("calendar unavailable")
        schedule_id = self._next_schedule_id
        self._next_schedule_id += 1
        self.scheduled[schedule_id] = {
            "scheduleId": schedule_id,
            "workoutId": int(workout_id),
            "date": date,
        }
        return {"scheduleId": schedule_id}

    def get_scheduled_workout_by_id(self, schedule_id):
        return deepcopy(self.scheduled[int(schedule_id)])


@pytest.mark.parametrize(
    "field,value",
    [
        ("workoutName", "Wrong name"),
        ("workoutName", None),
        ("sportType", {"sportTypeKey": "running"}),
        ("sportType", None),
    ],
)
def test_readback_template_identity_mismatch_prevents_scheduling(field, value):
    class ChangedIdentityClient(FakeGarminClient):
        def get_workout_by_id(self, workout_id):
            result = super().get_workout_by_id(workout_id)
            result[field] = value
            return result

    client = ChangedIdentityClient()
    result = publish_workout(
        client, strength_plan(), authorized=True,
        schedule_date="2026-09-13", journal_path=None,
    )
    assert result.template_state == "verification_failed"
    assert result.verified is False
    assert client.schedule_calls == 0
    assert any(field in error for error in result.verification_errors)


def test_template_only_creation_is_verified_without_scheduling():
    client = FakeGarminClient()

    result = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        journal_path=None,
    )

    assert result.template_state == "verified"
    assert result.schedule_state == "not_requested"
    assert result.workout_id == 100
    assert result.verified is True
    assert client.schedule_calls == 0


def test_explicit_schedule_date_wins_over_source_plan_date():
    client = FakeGarminClient()

    result = publish_workout(
        client,
        strength_plan(date="2026-09-12"),
        authorized=True,
        schedule_date="2026-09-13",
        journal_path=None,
    )

    assert result.template_state == "verified"
    assert result.schedule_state == "verified"
    assert result.schedule_date == "2026-09-13"
    assert client.scheduled[result.schedule_id]["date"] == "2026-09-13"


def test_readback_rest_mismatch_fails_before_scheduling():
    client = FakeGarminClient()
    client.drop_rest_on_read = True

    result = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        schedule_date="2026-09-13",
        journal_path=None,
    )

    assert result.template_state == "verification_failed"
    assert result.schedule_state == "not_attempted"
    assert result.workout_id == 100
    assert client.schedule_calls == 0


def test_calendar_failure_keeps_verified_template_id_and_separate_status():
    client = FakeGarminClient()
    client.fail_schedule = True

    result = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        schedule_date="2026-09-13",
        journal_path=None,
    )

    assert result.template_state == "verified"
    assert result.schedule_state == "failed"
    assert result.workout_id == 100
    assert result.schedule_id is None


def test_lost_upload_response_adopts_one_exact_remote_match():
    client = FakeGarminClient()
    client.timeout_after_upload = True

    result = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        journal_path=None,
    )

    assert result.state == "verified"
    assert result.workout_id == 100
    assert client.upload_calls == 1


def test_ambiguous_remote_matches_remain_uncertain_without_repost():
    client = FakeGarminClient()
    client.timeout_after_upload = True
    client.duplicate_on_timeout = True

    result = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        journal_path=None,
    )

    assert result.state == "uncertain"
    assert result.workout_id is None
    assert client.upload_calls == 1


def test_same_key_and_hash_reuses_verified_publication(tmp_path):
    client = FakeGarminClient()
    journal_path = tmp_path / "journal.json"
    plan = strength_plan()

    first = publish_workout(client, plan, authorized=True, journal_path=journal_path)
    second = publish_workout(client, plan, authorized=True, journal_path=journal_path)

    assert first.workout_id == second.workout_id == 100
    assert second.reused is True
    assert client.upload_calls == 1


def test_same_key_with_changed_content_is_a_conflict(tmp_path):
    client = FakeGarminClient()
    journal_path = tmp_path / "journal.json"

    publish_workout(client, strength_plan(), authorized=True, journal_path=journal_path)
    changed = strength_plan()
    changed = planned_workout_from_dict(
        {**changed.to_dict(), "name": "Changed Plan"}
    )

    with pytest.raises(PublicationConflictError, match="content"):
        publish_workout(client, changed, authorized=True, journal_path=journal_path)


def test_concurrent_same_key_uploads_only_once(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    client = FakeGarminClient()
    client.delay_upload = 0.03
    journal_path = tmp_path / "journal.json"
    plan = strength_plan()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: publish_workout(
                    client, plan, authorized=True, journal_path=journal_path
                ),
                range(2),
            )
        )

    assert {result.workout_id for result in results} == {100}
    assert client.upload_calls == 1
