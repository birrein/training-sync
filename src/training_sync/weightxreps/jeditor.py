"""Build Weight x Reps JEditorSaveRow payloads."""

from collections import Counter
from typing import Any

from training_sync.renderers.weightxreps_text import ParsedSetLine, ParsedTrainingDay

WEIGHT_X_REPS_SET_TYPE = 0


def build_jeditor_rows(
    day: ParsedTrainingDay,
    exercise_ids: dict[str, int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if day.body_weight_kg is not None:
        rows.append({"bw": day.body_weight_kg, "lb": 0})

    new_exercise_index = 0
    rows.append({"on": day.date})
    for exercise in day.exercises:
        exercise_row: dict[str, Any]
        if exercise.name in exercise_ids:
            exercise_row = {"eid": exercise_ids[exercise.name]}
        else:
            rows.append({"newExercise": exercise.name})
            exercise_row = {"eid": -new_exercise_index}
            new_exercise_index += 1

        exercise_row["erows"] = [
            _set_line_to_erow(set_line)
            for set_line in exercise.sets
        ]
        rows.append(exercise_row)
    return rows


def _set_line_to_erow(set_line: ParsedSetLine) -> dict[str, Any]:
    reps_counts = Counter(set_line.reps)
    if len(reps_counts) != 1:
        return {
            "w": _weight_payload(set_line),
            "r": set_line.reps[0],
            "s": 1,
            "type": WEIGHT_X_REPS_SET_TYPE,
            "c": "Unconsolidated reps: " + ", ".join(str(rep) for rep in set_line.reps),
        }

    reps, sets = next(iter(reps_counts.items()))
    return {
        "w": _weight_payload(set_line),
        "r": reps,
        "s": sets,
        "type": WEIGHT_X_REPS_SET_TYPE,
    }


def _weight_payload(set_line: ParsedSetLine) -> dict[str, Any]:
    payload = {"v": set_line.weight_kg, "lb": 0}
    if set_line.uses_bodyweight:
        payload["usebw"] = 1
    return payload
