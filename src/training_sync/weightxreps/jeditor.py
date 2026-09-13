"""Build Weight x Reps JEditorSaveRow payloads."""

from collections import Counter
from decimal import Decimal
from typing import Any

from training_sync.renderers.weightxreps_text import (
    DISTANCE_UNIT_KILOMETERS,
    ParsedSetLine,
    ParsedTrainingDay,
)

WEIGHT_X_REPS_SET_TYPE = 0


def build_jeditor_rows(
    day: ParsedTrainingDay,
    exercise_ids: dict[str, int | None],
) -> list[dict[str, Any]]:
    _validate_strength_semantics(day)
    rows: list[dict[str, Any]] = []
    if day.body_weight_kg is not None:
        rows.append({"bw": day.body_weight_kg, "lb": 0})

    new_exercise_index = 0
    rows.append({"on": day.date})
    for exercise in day.exercises:
        exercise_row: dict[str, Any]
        if exercise.name not in exercise_ids:
            raise ValueError(f"Exercise id resolution missing: {exercise.name}")

        exercise_id = exercise_ids[exercise.name]
        if exercise_id is None:
            rows.append({"newExercise": exercise.name})
            exercise_row = {"eid": -new_exercise_index}
            new_exercise_index += 1
        else:
            exercise_row = {"eid": exercise_id}

        exercise_row["erows"] = [
            _set_line_to_erow(set_line)
            for set_line in exercise.sets
        ]
        rows.append(exercise_row)
    return rows


def _set_line_to_erow(set_line: ParsedSetLine) -> dict[str, Any]:
    if set_line.set_type in (1, 2):
        return _cardio_erow(set_line)

    reps_counts = Counter(set_line.reps)
    if len(reps_counts) != 1:
        raise ValueError(
            "different repetition counts must use one line per physical set; "
            "do not consolidate them"
        )
    if len(set_line.reps) > 1 and set_line.rpe is not None:
        raise ValueError(
            "RPE must be attached to a single final set, not a consolidated line"
        )

    reps, sets = next(iter(reps_counts.items()))
    row = {
        "w": _weight_payload(set_line),
        "r": reps,
        "s": sets,
        "type": WEIGHT_X_REPS_SET_TYPE,
    }
    if set_line.rpe is not None:
        row["rpe"] = set_line.rpe
    return row


def _cardio_erow(set_line: ParsedSetLine) -> dict[str, Any]:
    if set_line.duration_ms is None:
        raise ValueError("Cardio set requires duration_ms")

    row: dict[str, Any] = {
        "w": 0,
        "r": 1,
        "s": 1,
        "type": set_line.set_type,
        "t": set_line.duration_ms,
    }
    if set_line.set_type == 2:
        if set_line.distance is None or set_line.distance_unit is None:
            raise ValueError("Distance cardio set requires distance and distance_unit")
        if set_line.distance_unit != DISTANCE_UNIT_KILOMETERS:
            raise ValueError(f"Unsupported distance unit: {set_line.distance_unit}")
        row["d"] = {
            "val": int(Decimal(str(set_line.distance)) * 100_000 * 100),
            "unit": set_line.distance_unit,
        }
    if set_line.comment:
        row["c"] = set_line.comment
    return row


def _weight_payload(set_line: ParsedSetLine) -> dict[str, Any]:
    payload = {"v": set_line.weight_kg, "lb": 0}
    if set_line.uses_bodyweight:
        payload["usebw"] = 1
    return payload


def _validate_strength_semantics(day: ParsedTrainingDay) -> None:
    for exercise in day.exercises:
        if not exercise.sets or not all(set_line.set_type == WEIGHT_X_REPS_SET_TYPE for set_line in exercise.sets):
            continue

        effort_indexes = [
            index
            for index, set_line in enumerate(exercise.sets)
            if set_line.rpe is not None
        ]
        if effort_indexes and effort_indexes != [len(exercise.sets) - 1]:
            raise ValueError(
                f"RPE for {exercise.name} must be attached to the final set"
            )
        if effort_indexes and len(exercise.sets[-1].reps) != 1:
            raise ValueError(
                f"RPE for {exercise.name} must be attached to a single final set"
            )
