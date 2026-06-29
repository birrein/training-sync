import pytest

from training_sync.renderers.weightxreps_text import (
    ParsedExercise,
    ParsedSetLine,
    ParsedTrainingDay,
)
from training_sync.weightxreps.jeditor import build_jeditor_rows


def test_build_jeditor_rows_uses_known_exercise_ids_and_bodyweight():
    day = ParsedTrainingDay(
        date="2026-06-19",
        body_weight_kg=71.4,
        exercises=[
            ParsedExercise(
                name="Chin Up",
                sets=[ParsedSetLine(weight_kg=0.0, reps=[5, 5, 5], uses_bodyweight=True)],
            ),
            ParsedExercise(
                name="Barbell Row",
                sets=[ParsedSetLine(weight_kg=51.0, reps=[12, 12, 12])],
            ),
        ],
    )

    rows = build_jeditor_rows(day, exercise_ids={"Chin Up": 10, "Barbell Row": 20})

    assert rows == [
        {"bw": 71.4, "lb": 0},
        {
            "on": "2026-06-19"
        },
        {
            "eid": 10,
            "erows": [{"w": {"v": 0.0, "lb": 0, "usebw": 1}, "r": 5, "s": 3, "type": 0}],
        },
        {
            "eid": 20,
            "erows": [{"w": {"v": 51.0, "lb": 0}, "r": 12, "s": 3, "type": 0}],
        },
    ]


def test_build_jeditor_rows_can_create_explicit_new_exercises():
    day = ParsedTrainingDay(
        date="2026-06-19",
        body_weight_kg=None,
        exercises=[
            ParsedExercise(
                name="New Lift",
                sets=[ParsedSetLine(weight_kg=10.0, reps=[8])],
            )
        ],
    )

    rows = build_jeditor_rows(day, exercise_ids={"New Lift": None})

    assert rows == [
        {
            "on": "2026-06-19"
        },
        {"newExercise": "New Lift"},
        {
            "eid": -1,
            "erows": [{"w": {"v": 10.0, "lb": 0}, "r": 8, "s": 1, "type": 0}],
        },
    ]


def test_build_jeditor_rows_rejects_missing_exercise_resolution():
    day = ParsedTrainingDay(
        date="2026-06-19",
        body_weight_kg=None,
        exercises=[
            ParsedExercise(
                name="New Lift",
                sets=[ParsedSetLine(weight_kg=10.0, reps=[8])],
            )
        ],
    )

    with pytest.raises(ValueError, match="Exercise id resolution missing: New Lift"):
        build_jeditor_rows(day, exercise_ids={})
