from garmin_sync.garmin_payloads import build_exercise_sets_payload
from garmin_sync.workouts import StrengthExercise, StrengthSet, StrengthWorkout, strength_workout_from_dict


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
            "weight": -1.0,
            "setType": "REST",
            "duration": 75.0,
            "startTime": None,
            "wktStepIndex": None,
            "messageIndex": None,
        },
    ]
