from training_sync.domain.body_weight import WeightReading, format_weight_tag
from training_sync.domain.strength_workout import (
    StrengthExercise,
    StrengthSet,
    StrengthWorkout,
    strength_workout_from_dict,
)
from training_sync.domain.training_entry import ActivityMetric, TrainingEntry


def test_strength_workout_from_dict_normalizes_fitbod_payload():
    workout = strength_workout_from_dict(
        {
            "date": "2026-06-19",
            "title": "Upper Body Day 2",
            "exercises": [
                {
                    "name": "Barbell Row",
                    "sets": [
                        {"reps": 8, "weight": 31},
                        {"reps": 12, "weight": 51},
                    ],
                }
            ],
        }
    )

    assert workout == StrengthWorkout(
        date="2026-06-19",
        title="Upper Body Day 2",
        exercises=[
            StrengthExercise(
                name="Barbell Row",
                sets=[
                    StrengthSet(reps=8, weight_kg=31.0),
                    StrengthSet(reps=12, weight_kg=51.0),
                ],
            )
        ],
    )


def test_weight_reading_formats_weightxreps_tag():
    reading = WeightReading(
        calendar_date="2026-06-18",
        weight_kg=71.389,
        source_type="INDEX_SCALE",
        day_delta=-1,
    )

    assert format_weight_tag(reading) == "@ 71.4 bw"


def test_training_entry_holds_activity_metrics():
    entry = TrainingEntry(
        date="2026-06-19",
        title="Upper Body Day 2",
        activity_type="strength_training",
        metrics=[
            ActivityMetric(label="Duration", value="01:11:20.3"),
            ActivityMetric(label="Avg HR", value="90"),
        ],
        body_weight=71.4,
        text_block="#Chin Up\nBW x 5, 5, 5",
    )

    assert entry.title == "Upper Body Day 2"
    assert entry.body_weight == 71.4
    assert entry.metrics[0].label == "Duration"
