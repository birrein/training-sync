import pytest

from training_sync.renderers.weightxreps_text import (
    DISTANCE_UNIT_KILOMETERS,
    ParsedExercise,
    ParsedSetLine,
    ParsedTrainingDay,
    parse_weightxreps_text,
    render_strength_text,
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


def test_render_strength_text_round_trips_strength_and_bodyweight_without_prior_cardio():
    prior = ParsedTrainingDay(
        date="2026-07-03",
        body_weight_kg=71.4,
        exercises=[
            ParsedExercise(
                name="Chin Up",
                sets=[ParsedSetLine(reps=(5, 5, 5), uses_bodyweight=True)],
            ),
            ParsedExercise(
                name="Barbell Row",
                sets=[
                    ParsedSetLine(weight_kg=31.0, reps=(8,)),
                    ParsedSetLine(weight_kg=51.0, reps=(12, 12, 12)),
                ],
            ),
            ParsedExercise(
                name="Running",
                sets=[
                    ParsedSetLine(
                        set_type=2,
                        duration_ms=900_000,
                        distance=2.5,
                        distance_unit="km",
                    )
                ],
            ),
        ],
    )

    rendered = render_strength_text(prior)

    assert rendered is not None
    assert parse_weightxreps_text(rendered) == ParsedTrainingDay(
        date="2026-07-03",
        body_weight_kg=71.4,
        exercises=prior.exercises[:2],
    )
    assert "#Running" not in rendered


@pytest.mark.parametrize(
    ("exercise_name", "expected_name"),
    [("Running", "Running"), ("Cycling", "Cycling"), ("Virtual_ride", "Cycling")],
)
def test_parse_weightxreps_text_builds_structured_distance_cardio(exercise_name, expected_name):
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
            name=expected_name,
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


def test_parse_weightxreps_text_does_not_normalize_strength_exercise_names():
    parsed = parse_weightxreps_text(
        """2026-07-03

#Cycling Russian Twist
10kg x 12, 12
"""
    )

    assert parsed.exercises[0].name == "Cycling Russian Twist"


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


def test_parse_weightxreps_text_ignores_garmin_strength_activity_block():
    parsed = parse_weightxreps_text(
        """2026-07-03

#Strength_training
@ Duration: 00:45:00.0
"""
    )

    assert parsed.exercises == []


def test_parse_weightxreps_text_rejects_malformed_strength_set_lines():
    with pytest.raises(ValueError, match="Unsupported set line: not a valid set"):
        parse_weightxreps_text(
            """2026-07-03

#Barbell Row
not a valid set
"""
        )


def test_parse_and_render_strength_rpe_suffix():
    parsed = parse_weightxreps_text(
        """2026-07-03

#Barbell Row
51kg x 8 @9 rpe
"""
    )

    assert parsed.exercises[0].sets[0].rpe == 9
    assert "51kg x 8 @9 rpe" in render_strength_text(parsed)
