import pytest

from training_sync.renderers.weightxreps_text import (
    DISTANCE_UNIT_KILOMETERS,
    ParsedExercise,
    ParsedSetLine,
    ParsedTrainingDay,
)
from training_sync.weightxreps.jeditor import _set_line_to_erow, build_jeditor_rows


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
            "eid": 0,
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


def test_set_line_to_erow_encodes_distance_cardio_with_exact_supported_unit():
    distance_set = ParsedSetLine(
        set_type=2,
        duration_ms=3_620_000,
        distance=27.95,
        distance_unit=DISTANCE_UNIT_KILOMETERS,
        comment="Zwift Ride | Avg HR: 148 | Elev Gain: 158 m",
    )

    assert _set_line_to_erow(distance_set) == {
        "type": 2,
        "t": 3_620_000,
        "d": {"val": 279_500_000, "unit": "km"},
        "c": "Zwift Ride | Avg HR: 148 | Elev Gain: 158 m",
    }


def test_set_line_to_erow_encodes_duration_only_cardio_without_distance_fields():
    assert _set_line_to_erow(ParsedSetLine(set_type=1, duration_ms=1_800_000)) == {
        "type": 1,
        "t": 1_800_000,
    }
    assert _set_line_to_erow(
        ParsedSetLine(set_type=1, duration_ms=1_800_000, comment="Recovery Ride")
    ) == {
        "type": 1,
        "t": 1_800_000,
        "c": "Recovery Ride",
    }


def test_set_line_to_erow_preserves_strength_payload_shape():
    assert _set_line_to_erow(
        ParsedSetLine(weight_kg=51.0, reps=(12, 12, 12))
    ) == {"w": {"v": 51.0, "lb": 0}, "r": 12, "s": 3, "type": 0}
    assert _set_line_to_erow(
        ParsedSetLine(weight_kg=0.0, reps=(5, 5, 5), uses_bodyweight=True)
    ) == {"w": {"v": 0.0, "lb": 0, "usebw": 1}, "r": 5, "s": 3, "type": 0}
