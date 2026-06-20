from training_sync.renderers.weightxreps_text import (
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
                sets=[ParsedSetLine(weight_kg=0.0, reps=[5, 5, 5], uses_bodyweight=True)],
            ),
            ParsedExercise(
                name="Barbell Row",
                sets=[
                    ParsedSetLine(weight_kg=31.0, reps=[8], uses_bodyweight=False),
                    ParsedSetLine(weight_kg=51.0, reps=[12, 12, 12], uses_bodyweight=False),
                ],
            ),
        ],
    )
