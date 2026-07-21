import pytest

from training_sync.domain.strength_workout import (
    StrengthExercise,
    StrengthSet,
    StrengthWorkout,
    strength_workout_from_dict,
)
from training_sync.garmin.import_strength import push_workout
from training_sync.garmin.payloads import build_exercise_sets_payload


def test_strength_workout_from_dict_normalizes_fitbod_payload():
    workout = strength_workout_from_dict(
        {
            "date": "2026-06-15",
            "title": "Upper Body Day",
            "exercises": [
                {
                    "name": "Barbell Bench Press",
                    "sets": [
                        {"reps": 10, "weight": 20},
                        {"reps": 8, "weight": 40.5},
                    ],
                }
            ],
        },
        default_date="2026-01-01",
    )

    assert workout == StrengthWorkout(
        date="2026-06-15",
        title="Upper Body Day",
        exercises=[
            StrengthExercise(
                name="Barbell Bench Press",
                sets=[
                    StrengthSet(reps=10, weight_kg=20.0),
                    StrengthSet(reps=8, weight_kg=40.5),
                ],
            )
        ],
    )


def test_build_exercise_sets_payload_adds_rest_sets_and_preserves_existing_timing():
    workout = StrengthWorkout(
        date="2026-06-15",
        title="Upper Body Day",
        exercises=[
            StrengthExercise(
                name="Barbell Bench Press",
                sets=[StrengthSet(reps=10, weight_kg=20.5)],
            )
        ],
    )
    existing_sets = [
        {"duration": 42.0, "startTime": "2026-06-15T10:00:00.0"},
        {"duration": 75.0, "startTime": "2026-06-15T10:00:42.0"},
    ]
    garmin_dict = {
        "BARBELL BENCH PRESS": {
            "category": "BENCH_PRESS",
            "name": "BARBELL_BENCH_PRESS",
        }
    }

    payload = build_exercise_sets_payload(workout, existing_sets, garmin_dict)

    assert payload == [
        {
            "exercises": [
                {
                    "category": "BENCH_PRESS",
                    "name": "BARBELL_BENCH_PRESS",
                    "probability": 100.0,
                }
            ],
            "repetitionCount": 10,
            "weight": 20500.0,
            "setType": "ACTIVE",
            "duration": 42.0,
            "startTime": "2026-06-15T10:00:00.0",
            "wktStepIndex": None,
            "messageIndex": None,
        },
        {
            "exercises": [],
            "repetitionCount": None,
            "weight": None,
            "setType": "REST",
            "duration": 75.0,
            "startTime": "2026-06-15T10:00:42.0",
            "wktStepIndex": None,
            "messageIndex": None,
        },
    ]


def test_build_exercise_sets_payload_extends_existing_sets_with_indices_and_times():
    workout = StrengthWorkout(
        date="2026-06-15",
        title="Upper Body Day",
        exercises=[
            StrengthExercise(
                name="Barbell Bench Press",
                sets=[
                    StrengthSet(reps=10, weight_kg=20.5),
                    StrengthSet(reps=8, weight_kg=30),
                ],
            )
        ],
    )
    existing_sets = [
        {
            "duration": 42.0,
            "startTime": "2026-06-15T10:00:00.0",
            "messageIndex": 0,
            "wktStepIndex": 7,
            "setType": "ACTIVE",
            "weight": 1000,
        },
        {
            "duration": 75.0,
            "startTime": "2026-06-15T10:00:42.0",
            "messageIndex": 1,
            "wktStepIndex": 8,
            "setType": "REST",
            "weight": None,
        },
    ]
    garmin_dict = {
        "BARBELL BENCH PRESS": {
            "category": "BENCH_PRESS",
            "name": "BARBELL_BENCH_PRESS",
        }
    }

    payload = build_exercise_sets_payload(workout, existing_sets, garmin_dict)

    assert len(payload) == 4
    assert payload[0]["messageIndex"] == 0
    assert payload[0]["startTime"] == "2026-06-15T10:00:00.0"
    assert payload[0]["wktStepIndex"] == 7
    assert payload[1]["messageIndex"] == 1
    assert payload[1]["startTime"] == "2026-06-15T10:00:42.0"
    assert payload[1]["wktStepIndex"] == 8
    assert payload[2]["messageIndex"] == 2
    assert payload[2]["startTime"] == "2026-06-15T10:01:57.0"
    assert payload[2]["setType"] == "ACTIVE"
    assert payload[2]["repetitionCount"] == 8
    assert payload[2]["weight"] == 30000.0
    assert payload[3]["messageIndex"] == 3
    assert payload[3]["startTime"] == "2026-06-15T10:02:27.0"
    assert payload[3]["setType"] == "REST"
    assert payload[3]["weight"] is None


class FakeGarminClient:
    def __init__(self, saved_sets):
        self.saved_sets = saved_sets
        self.submitted_payload = None

    def get_activities_by_date(self, start, end):
        return [
            {
                "activityId": 123,
                "activityName": "Strength",
                "activityType": {"typeKey": "strength_training"},
            }
        ]

    def set_activity_name(self, activity_id, title):
        pass

    def get_activity_exercise_sets(self, activity_id):
        if self.submitted_payload is not None:
            return {"exerciseSets": self.saved_sets}
        return {
            "exerciseSets": [
                {
                    "duration": 30.0,
                    "startTime": "2026-06-15T10:00:00.0",
                    "messageIndex": 0,
                    "setType": "ACTIVE",
                },
                {
                    "duration": 60.0,
                    "startTime": "2026-06-15T10:00:30.0",
                    "messageIndex": 1,
                    "setType": "REST",
                },
            ]
        }

    def set_activity_exercise_sets(self, activity_id, payload):
        self.submitted_payload = payload


def test_push_workout_raises_when_garmin_does_not_persist_expected_sets():
    client = FakeGarminClient(
        saved_sets=[
            {
                "exercises": [
                    {
                        "category": "BENCH_PRESS",
                        "name": "BARBELL_BENCH_PRESS",
                        "probability": 100.0,
                    }
                ],
                "repetitionCount": 9,
                "weight": 20500.0,
                "setType": "ACTIVE",
            },
        ]
    )

    with pytest.raises(RuntimeError, match="Garmin did not persist"):
        push_workout(
            client,
            {
                "date": "2026-06-15",
                "title": "Upper Body Day",
                "exercises": [
                    {
                        "name": "Barbell Bench Press",
                        "sets": [{"reps": 10, "weight": 20.5}],
                    }
                ],
            },
        )
