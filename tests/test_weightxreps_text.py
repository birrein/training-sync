import pytest

from training_sync.renderers.weightxreps_text import (
    DISTANCE_UNIT_KILOMETERS,
    ParsedExercise,
    ParsedSetLine,
    ParsedTrainingDay,
    parse_weightxreps_text,
)


def test_parse_weightxreps_text_handles_bodyweight_and_weighted_sets():
    parsed = parse_weightxreps_text(
        """2026-06-19
@ 71.4 bw
@ Duration: 01:11:20.3

#Chin Up
BW x 5, 5, 5

#Barbell Row
31kg x 8
51kg x 12, 12, 12
"""
    )

    assert parsed == ParsedTrainingDay(
        date="2026-06-19",
        body_weight_kg=71.4,
        exercises=[
            ParsedExercise(
                name="Chin Up",
                sets=[ParsedSetLine(weight_kg=0.0, reps=(5, 5, 5), uses_bodyweight=True)],
            ),
            ParsedExercise(
                name="Barbell Row",
                sets=[
                    ParsedSetLine(weight_kg=31.0, reps=(8,), uses_bodyweight=False),
                    ParsedSetLine(weight_kg=51.0, reps=(12, 12, 12), uses_bodyweight=False),
                ],
            ),
        ],
    )


@pytest.mark.parametrize("exercise_name", ["Running", "Cycling", "Virtual_ride"])
def test_parse_weightxreps_text_builds_structured_distance_cardio(exercise_name):
    parsed = parse_weightxreps_text(
        f"""2026-07-03

#{exercise_name}
27.95km
@ Duration: 01:00:20.0
@ Avg HR: 148
@ Elev Gain: 158
"""
    )

    assert parsed.exercises == [
        ParsedExercise(
            name=exercise_name,
            sets=[
                ParsedSetLine(
                    set_type=2,
                    duration_ms=3_620_000,
                    distance=27.95,
                    distance_unit=DISTANCE_UNIT_KILOMETERS,
                    comment="Avg HR: 148 | Elev Gain: 158",
                )
            ],
        )
    ]


def test_parse_weightxreps_text_builds_duration_only_cardio_without_invented_metrics():
    parsed = parse_weightxreps_text(
        """2026-07-03

#Cycling
@ Duration: 00:30:00.0
@ Calories: 250
"""
    )

    assert parsed.exercises == [
        ParsedExercise(
            name="Cycling",
            sets=[
                ParsedSetLine(
                    set_type=1,
                    duration_ms=1_800_000,
                    comment="Calories: 250",
                )
            ],
        )
    ]
