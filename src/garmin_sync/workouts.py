"""Backward-compatible imports for strength workout domain objects."""

from training_sync.domain.strength_workout import (
    StrengthExercise,
    StrengthSet,
    StrengthWorkout,
    strength_workout_from_dict,
)

__all__ = [
    "StrengthExercise",
    "StrengthSet",
    "StrengthWorkout",
    "strength_workout_from_dict",
]
