"""Local Weight x Reps exercise mapping."""

from dataclasses import dataclass
from pathlib import Path
import re

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib


@dataclass(frozen=True)
class ExerciseMapping:
    weightxreps_name: str
    weightxreps_id: int | None
    aliases: list[str]
    create_if_missing: bool = False


class DuplicateExerciseAliasError(ValueError):
    def __init__(self, alias: str, targets: list[str]) -> None:
        self.alias = alias
        self.targets = targets
        super().__init__(
            f"Duplicate Weight x Reps exercise alias '{alias}' maps to: {', '.join(targets)}"
        )


def load_exercise_mappings(path: Path) -> list[ExerciseMapping]:
    if not path.exists():
        return []

    with path.open("rb") as handle:
        data = tomllib.load(handle)

    mappings = [
        ExerciseMapping(
            weightxreps_name=exercise["weightxreps_name"],
            weightxreps_id=exercise.get("weightxreps_id"),
            aliases=list(exercise.get("aliases") or []),
            create_if_missing=bool(exercise.get("create_if_missing", False)),
        )
        for exercise in data.get("exercises", [])
    ]
    _validate_unique_aliases(mappings)
    return mappings


def normalize_exercise_name(name: str) -> str:
    without_hash = name.strip().removeprefix("#").strip().lower()
    without_punctuation = re.sub(r"[^\w\s]", " ", without_hash)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def _validate_unique_aliases(mappings: list[ExerciseMapping]) -> None:
    seen: dict[str, tuple[int, ExerciseMapping]] = {}
    for mapping_index, mapping in enumerate(mappings):
        for raw_name in [mapping.weightxreps_name, *mapping.aliases]:
            alias = normalize_exercise_name(raw_name)
            existing = seen.get(alias)
            if existing is not None and existing[0] != mapping_index:
                existing_mapping = existing[1]
                raise DuplicateExerciseAliasError(
                    alias,
                    _duplicate_targets(existing_mapping, mapping),
                )
            seen[alias] = (mapping_index, mapping)


def _duplicate_targets(
    existing_mapping: ExerciseMapping,
    mapping: ExerciseMapping,
) -> list[str]:
    if existing_mapping.weightxreps_name == mapping.weightxreps_name:
        return [_target_with_id(existing_mapping), _target_with_id(mapping)]

    return [existing_mapping.weightxreps_name, mapping.weightxreps_name]


def _target_with_id(mapping: ExerciseMapping) -> str:
    if mapping.weightxreps_id is None:
        return f"{mapping.weightxreps_name} (id=None)"

    return f"{mapping.weightxreps_name} (id={mapping.weightxreps_id})"
