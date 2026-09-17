from __future__ import annotations

from copy import deepcopy
import json
from threading import Lock
import time

import pytest

from training_sync.domain.planned_workout import planned_workout_from_dict
from training_sync.use_cases.publish_workout import (
    PublicationConflictError,
    build_publication_marker,
    publish_workout,
)
from training_sync.garmin.planned_workouts import project_planned_workout


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


class ProviderBoundaryGarminClient(FakeGarminClient):
    """Reject application-only fields and incompatible provider wire types."""

    def upload_workout(self, payload):
        sport_type = payload.get("sportType") or {}
        if sport_type.get("sportTypeKey") == "strength_training":
            assert sport_type.get("displayOrder") == 4
        for step in payload["workoutSegments"][0]["workoutSteps"]:
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
                unit = step.get("weightUnit")
                assert isinstance(unit, dict)
                assert unit == {
                    "unitId": 8,
                    "unitKey": "kilogram",
                    "factor": 1000.0,
                }
            if sport_type.get("sportTypeKey") == "strength_training":
                assert step.get("preferredEndConditionUnit") is None
        return super().upload_workout(payload)


class GarminHttp500Error(RuntimeError):
    status_code = 500

    def __str__(self):
        return (
            "API Error 500 - {'clientMessage': 'Reference Error ID in error logs '"
            "for further information', 'errorId': 'ref-500-sanitized', "
            "'error': 'MismatchedInputException', "
            "'authorization': 'Bearer super-secret-token', "
            "'requestBody': 'private workout payload'}"
        )


class Http500UploadClient(FakeGarminClient):
    def upload_workout(self, payload):
        self.upload_calls += 1
        raise GarminHttp500Error()


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
    assert result.diagnostics == {
        "stage": "upload",
        "provider_error_type": "TimeoutError",
    }
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


def _publish_with_readback_mutation(mutator):
    class MutatedReadbackClient(FakeGarminClient):
        def get_workout_by_id(self, workout_id):
            result = super().get_workout_by_id(workout_id)
            mutator(result["workoutSegments"][0]["workoutSteps"])
            return result

    client = MutatedReadbackClient()
    result = publish_workout(client, strength_plan(), authorized=True, journal_path=None)
    return client, result


def test_readback_accepts_structured_kilogram_or_legacy_gram_encoding():
    def use_legacy_grams(steps):
        for step in steps:
            if step.get("weightValue") is not None:
                step["weightValue"] = step["weightValue"] * 1000
                step["weightUnit"] = "gram"
                step.pop("repetitionCount", None)

    client, result = _publish_with_readback_mutation(use_legacy_grams)

    assert result.template_state == "verified"
    assert result.verified is True
    assert client.upload_calls == 1


def test_unknown_weight_unit_fails_verification_instead_of_defaulting_to_grams():
    def use_unknown_unit(steps):
        for step in steps:
            if step.get("weightValue") is not None:
                step["weightUnit"] = "mystery-unit"

    client, result = _publish_with_readback_mutation(use_unknown_unit)

    assert result.template_state == "verification_failed"
    assert result.schedule_state == "not_requested"
    assert any("load value/unit" in error for error in result.verification_errors)
    assert client.schedule_calls == 0


def test_contradictory_structured_weight_unit_fails_verification():
    def use_contradictory_unit(steps):
        for step in steps:
            if step.get("weightValue") is not None:
                step["weightUnit"] = {
                    "unitId": 8,
                    "unitKey": "kilogram",
                    "factor": 1.0,
                }

    client, result = _publish_with_readback_mutation(use_contradictory_unit)

    assert result.template_state == "verification_failed"
    assert any("load value/unit" in error for error in result.verification_errors)
    assert client.schedule_calls == 0


def test_missing_dragon_flag_comment_fails_verification():
    plan = planned_workout_from_dict(
        {
            **strength_plan().to_dict(),
            "key": "publishable-dragon-flag",
            "exercises": [
                {
                    "name": "Dragon Flag",
                    "garmin_name": "Reverse Crunch on a Bench",
                    "sets": [{"reps": 8, "load": {"kind": "bodyweight"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": None,
                }
            ],
        }
    )

    def remove_original_comment(steps):
        for step in steps:
            step["description"] = step.get("description", "").replace("Dragon Flag", "")

    class DragonReadbackClient(FakeGarminClient):
        def get_workout_by_id(self, workout_id):
            result = super().get_workout_by_id(workout_id)
            remove_original_comment(result["workoutSegments"][0]["workoutSteps"])
            return result

    client = DragonReadbackClient()
    result = publish_workout(client, plan, authorized=True, journal_path=None)

    assert result.template_state == "verification_failed"
    assert any("description/side semantics" in error for error in result.verification_errors)
    assert client.schedule_calls == 0


def test_missing_per_hand_instruction_fails_even_when_mass_matches():
    plan = planned_workout_from_dict(
        {
            **strength_plan().to_dict(),
            "key": "publishable-per-hand",
            "exercises": [
                {
                    "name": "Dumbbell Lateral Raise",
                    "sets": [
                        {
                            "reps": 15,
                            "load": {"kind": "mass", "kg": 12.5, "basis": "per_hand"},
                        }
                    ],
                    "rest_between_sets": None,
                    "rest_after_exercise": None,
                }
            ],
        }
    )

    class PerHandReadbackClient(FakeGarminClient):
        def get_workout_by_id(self, workout_id):
            result = super().get_workout_by_id(workout_id)
            for step in result["workoutSegments"][0]["workoutSteps"]:
                step["description"] = step.get("description", "").replace("per hand", "")
            return result

    client = PerHandReadbackClient()
    result = publish_workout(client, plan, authorized=True, journal_path=None)

    assert result.template_state == "verification_failed"
    assert any("description/side semantics" in error for error in result.verification_errors)
    assert client.schedule_calls == 0


def test_mismatched_mass_fails_verification_and_never_schedules():
    def change_mass(steps):
        for step in steps:
            if step.get("weightValue") is not None:
                step["weightValue"] = step["weightValue"] + 1

    client, result = _publish_with_readback_mutation(change_mass)

    assert result.template_state == "verification_failed"
    assert any("load value/unit" in error for error in result.verification_errors)
    assert client.schedule_calls == 0


def test_provider_boundary_accepts_corrected_payload_and_readback():
    client = ProviderBoundaryGarminClient()

    result = publish_workout(client, strength_plan(), authorized=True, journal_path=None)

    assert result.template_state == "verified"
    assert result.workout_id == 100


def test_uncertain_journal_adopts_one_corrected_remote_and_reuses_existing_schedule(tmp_path):
    client = ProviderBoundaryGarminClient()
    plan = strength_plan()
    projection = project_planned_workout(plan)
    marker = build_publication_marker(plan)
    remote = deepcopy(projection.payload)
    remote["description"] = f"{remote['description']} | {marker}"
    remote["workoutId"] = 700
    client.workouts[700] = remote
    client.scheduled[901] = {
        "scheduleId": 901,
        "workoutId": 700,
        "date": "2026-09-16",
    }
    journal_path = tmp_path / "journal.json"
    journal_key = f"default\0{plan.key}"
    journal_path.write_text(
        json.dumps(
            {
                "entries": {
                    journal_key: {
                        "account_plan_key": journal_key,
                        "plan_key": plan.key,
                        "execution_hash": plan.execution_hash(),
                        "marker": marker,
                        "state": "uncertain",
                        "schedule_id": 901,
                        "schedule_date": "2026-09-16",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = publish_workout(
        client,
        plan,
        authorized=True,
        schedule_date="2026-09-16",
        journal_path=journal_path,
    )

    assert result.state == "scheduled"
    assert result.workout_id == 700
    assert result.schedule_id == 901
    assert result.reused is True
    assert client.upload_calls == 0
    assert client.schedule_calls == 0


def test_incomplete_reconciliation_keeps_uncertain_state_and_does_not_reupload(tmp_path):
    class IncompleteInventoryClient(ProviderBoundaryGarminClient):
        def get_workouts(self, start=0, limit=100):
            return [
                {
                    "workoutId": f"decoy-{start + index}",
                    "description": "unrelated sanitized workout",
                }
                for index in range(limit)
            ]

    client = IncompleteInventoryClient()
    client.timeout_after_upload = True
    journal_path = tmp_path / "journal.json"
    first = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        journal_path=journal_path,
    )
    second = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        journal_path=journal_path,
    )

    assert first.state == "uncertain"
    assert second.state == "uncertain"
    assert "incomplete" in (first.error or "")
    assert client.upload_calls == 1


def test_provider_boundary_readback_missing_rest_fails_without_scheduling():
    class MissingRestClient(ProviderBoundaryGarminClient):
        def get_workout_by_id(self, workout_id):
            result = super().get_workout_by_id(workout_id)
            steps = result["workoutSegments"][0]["workoutSteps"]
            result["workoutSegments"][0]["workoutSteps"] = [
                step for step in steps if step["stepType"]["stepTypeKey"] != "rest"
            ]
            return result

    client = MissingRestClient()
    result = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        schedule_date="2026-09-16",
        journal_path=None,
    )

    assert result.template_state == "verification_failed"
    assert client.schedule_calls == 0


def test_http_500_keeps_allowlisted_diagnostics_and_redacts_journal(tmp_path):
    client = Http500UploadClient()
    journal_path = tmp_path / "journal.json"

    result = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        journal_path=journal_path,
    )

    expected = {
        "stage": "upload",
        "http_status": 500,
        "provider_error_type": "MismatchedInputException",
        "reference_id": "ref-500-sanitized",
    }
    assert result.state == "uncertain"
    assert result.diagnostics == expected
    journal_text = journal_path.read_text(encoding="utf-8")
    assert json.loads(journal_text)["entries"]
    assert expected in [
        entry["diagnostics"]
        for entry in json.loads(journal_text)["entries"].values()
    ]
    assert "super-secret-token" not in journal_text
    assert "private workout payload" not in journal_text
    assert len(journal_text) < 2000


def test_timeout_only_failure_reports_stage_without_inventing_provider_details(tmp_path):
    class TimeoutWithoutRemoteClient(FakeGarminClient):
        def upload_workout(self, payload):
            self.upload_calls += 1
            raise TimeoutError("request body contains secret-token")

    client = TimeoutWithoutRemoteClient()
    result = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        journal_path=tmp_path / "journal.json",
    )

    assert result.state == "uncertain"
    assert result.diagnostics == {
        "stage": "upload",
        "provider_error_type": "TimeoutError",
    }
    assert "secret-token" not in (result.error or "")


def test_http_500_diagnostic_survives_incomplete_reconciliation_without_retry(tmp_path):
    class IncompleteHttp500Client(Http500UploadClient):
        def get_workouts(self, start=0, limit=100):
            return [
                {
                    "workoutId": f"decoy-{start + index}",
                    "description": "unrelated sanitized workout",
                }
                for index in range(limit)
            ]

    client = IncompleteHttp500Client()
    journal_path = tmp_path / "journal.json"
    first = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        journal_path=journal_path,
    )
    second = publish_workout(
        client,
        strength_plan(),
        authorized=True,
        journal_path=journal_path,
    )

    assert first.state == "uncertain"
    assert second.state == "uncertain"
    assert first.diagnostics == second.diagnostics
    assert "incomplete" in (second.error or "")
    assert client.upload_calls == 1
