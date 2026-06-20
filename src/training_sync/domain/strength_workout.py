"""Strength workout domain objects and input normalization."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class StrengthSet:
    reps: int
    weight_kg: float


@dataclass(frozen=True)
class StrengthExercise:
    name: str
    sets: list[StrengthSet]


@dataclass(frozen=True)
class StrengthWorkout:
    date: str
    title: str | None
    exercises: list[StrengthExercise]


def strength_workout_from_dict(
    workout_data: dict[str, Any],
    default_date: str | None = None,
) -> StrengthWorkout:
    """Normalize Fitbod-like workout data into a strength workout."""
    date = (
        workout_data.get("date")
        or default_date
        or datetime.today().strftime("%Y-%m-%d")
    )
    exercises = [
        StrengthExercise(
            name=exercise.get("name", "UNKNOWN"),
            sets=[
                StrengthSet(
                    reps=int(raw_set.get("reps", 0)),
                    weight_kg=float(raw_set.get("weight", 0)),
                )
                for raw_set in exercise.get("sets", [])
            ],
        )
        for exercise in workout_data.get("exercises", [])
    ]

    return StrengthWorkout(
        date=date,
        title=workout_data.get("title"),
        exercises=exercises,
    )
