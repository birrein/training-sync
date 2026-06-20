"""Build Garmin payloads from normalized workouts."""

from garmin_sync.mapper import get_mapping
from garmin_sync.workouts import StrengthWorkout

GRAMS_PER_KG = 1000.0
DEFAULT_ACTIVE_DURATION = 30.0
DEFAULT_REST_DURATION = 60.0
REST_WEIGHT = -1.0


def build_exercise_sets_payload(
    workout: StrengthWorkout,
    existing_sets: list[dict],
    garmin_dict: dict,
) -> list[dict]:
    """Build the Garmin ACTIVE/REST exercise sets payload for a strength workout."""
    sets_payload = []
    existing_index = 0

    for exercise in workout.exercises:
        mapping = get_mapping(exercise.name, garmin_dict)

        for workout_set in exercise.sets:
            active_base = _existing_set(existing_sets, existing_index)
            sets_payload.append(
                {
                    "exercises": [mapping],
                    "repetitionCount": workout_set.reps,
                    "weight": workout_set.weight_kg * GRAMS_PER_KG,
                    "setType": "ACTIVE",
                    "duration": active_base.get("duration", DEFAULT_ACTIVE_DURATION),
                    "startTime": active_base.get("startTime"),
                    "wktStepIndex": None,
                    "messageIndex": None,
                }
            )
            existing_index += 1

            rest_base = _existing_set(existing_sets, existing_index)
            sets_payload.append(
                {
                    "exercises": [],
                    "repetitionCount": None,
                    "weight": REST_WEIGHT,
                    "setType": "REST",
                    "duration": rest_base.get("duration", DEFAULT_REST_DURATION),
                    "startTime": None,
                    "wktStepIndex": None,
                    "messageIndex": None,
                }
            )
            existing_index += 1

    return sets_payload


def _existing_set(existing_sets: list[dict], index: int) -> dict:
    if index >= len(existing_sets):
        return {}
    return existing_sets[index]
