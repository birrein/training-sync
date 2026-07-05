"""Build Garmin payloads from normalized workouts."""

from datetime import datetime, timedelta

from garmin_sync.mapper import get_mapping
from garmin_sync.workouts import StrengthWorkout

GRAMS_PER_KG = 1000.0
DEFAULT_ACTIVE_DURATION = 30.0
DEFAULT_REST_DURATION = 60.0
REST_WEIGHT = None


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
            active_base_exists = existing_index < len(existing_sets)
            active_start = (
                active_base.get("startTime")
                if active_base_exists
                else _next_start_time(sets_payload)
            )
            sets_payload.append(
                _exercise_set_row(
                    active_base,
                    row_index=len(sets_payload),
                    base_exists=active_base_exists,
                    updates={
                        "exercises": [mapping],
                        "repetitionCount": workout_set.reps,
                        "weight": workout_set.weight_kg * GRAMS_PER_KG,
                        "setType": "ACTIVE",
                        "duration": active_base.get("duration", DEFAULT_ACTIVE_DURATION),
                        "startTime": active_start,
                    },
                )
            )
            existing_index += 1

            rest_base = _existing_set(existing_sets, existing_index)
            rest_base_exists = existing_index < len(existing_sets)
            rest_start = (
                rest_base.get("startTime")
                if rest_base_exists
                else _next_start_time(sets_payload)
            )
            sets_payload.append(
                _exercise_set_row(
                    rest_base,
                    row_index=len(sets_payload),
                    base_exists=rest_base_exists,
                    updates={
                        "exercises": [],
                        "repetitionCount": None,
                        "weight": REST_WEIGHT,
                        "setType": "REST",
                        "duration": rest_base.get("duration", DEFAULT_REST_DURATION),
                        "startTime": rest_start,
                    },
                )
            )
            existing_index += 1

    return sets_payload


def _existing_set(existing_sets: list[dict], index: int) -> dict:
    if index >= len(existing_sets):
        return {}
    return existing_sets[index]


def _exercise_set_row(
    base: dict,
    *,
    row_index: int,
    base_exists: bool,
    updates: dict,
) -> dict:
    row = dict(base)
    row.update(updates)
    row["wktStepIndex"] = base.get("wktStepIndex") if base_exists else None
    row["messageIndex"] = base.get("messageIndex") if base_exists else row_index
    return row


def _next_start_time(rows: list[dict]) -> str | None:
    if not rows:
        return None

    previous = rows[-1]
    start_time = previous.get("startTime")
    if not start_time:
        return None

    duration = previous.get("duration")
    if duration is None:
        return start_time

    try:
        next_time = datetime.fromisoformat(start_time) + timedelta(seconds=float(duration))
    except (TypeError, ValueError):
        return None
    return next_time.replace(microsecond=0).isoformat() + ".0"
