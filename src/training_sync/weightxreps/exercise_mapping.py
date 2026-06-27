"""Local Weight x Reps exercise mapping."""

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib


@dataclass(frozen=True)
class ExerciseMapping:
    weightxreps_name: str
    weightxreps_id: int | None
    aliases: list[str]


def load_exercise_mappings(path: Path) -> list[ExerciseMapping]:
    if not path.exists():
        return []

    with path.open("rb") as handle:
        data = tomllib.load(handle)

    return [
        ExerciseMapping(
            weightxreps_name=exercise["weightxreps_name"],
            weightxreps_id=exercise.get("weightxreps_id"),
            aliases=list(exercise.get("aliases") or []),
        )
        for exercise in data.get("exercises", [])
    ]
