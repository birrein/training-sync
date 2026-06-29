"""Local Weight x Reps exercise mapping."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil

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


def add_alias_mapping(
    path: Path,
    incoming_name: str,
    weightxreps_name: str,
    weightxreps_id: int,
) -> None:
    mappings = load_exercise_mappings(path)
    updated = _merge_alias(mappings, incoming_name, weightxreps_name, weightxreps_id)
    _backup_if_exists(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_exercise_mappings(updated), encoding="utf-8")
    path.chmod(0o600)


def normalize_exercise_name(name: str) -> str:
    without_hash = name.strip().removeprefix("#").strip().lower()
    without_punctuation = re.sub(r"[^\w\s]", " ", without_hash)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def _merge_alias(
    mappings: list[ExerciseMapping],
    incoming_name: str,
    weightxreps_name: str,
    weightxreps_id: int,
) -> list[ExerciseMapping]:
    updated: list[ExerciseMapping] = []
    matched = False

    for mapping in mappings:
        if mapping.weightxreps_name == weightxreps_name:
            updated.append(
                ExerciseMapping(
                    weightxreps_name=weightxreps_name,
                    weightxreps_id=weightxreps_id,
                    aliases=_sorted_unique(
                        [
                            mapping.weightxreps_name,
                            *mapping.aliases,
                            incoming_name,
                        ]
                    ),
                    create_if_missing=mapping.create_if_missing,
                )
            )
            matched = True
        else:
            updated.append(
                ExerciseMapping(
                    weightxreps_name=mapping.weightxreps_name,
                    weightxreps_id=mapping.weightxreps_id,
                    aliases=_sorted_unique(mapping.aliases),
                    create_if_missing=mapping.create_if_missing,
                )
            )

    if not matched:
        updated.append(
            ExerciseMapping(
                weightxreps_name=weightxreps_name,
                weightxreps_id=weightxreps_id,
                aliases=_sorted_unique([weightxreps_name, incoming_name]),
            )
        )

    _validate_unique_aliases(updated)
    return sorted(updated, key=lambda mapping: mapping.weightxreps_name.casefold())


def _backup_if_exists(path: Path) -> None:
    if not path.exists():
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    backup_path.chmod(0o600)


def _dump_exercise_mappings(mappings: list[ExerciseMapping]) -> str:
    blocks = [_dump_exercise_mapping(mapping) for mapping in mappings]
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _dump_exercise_mapping(mapping: ExerciseMapping) -> str:
    lines = [
        "[[exercises]]",
        f"weightxreps_name = {_toml_string(mapping.weightxreps_name)}",
    ]
    if mapping.weightxreps_id is not None:
        lines.append(f"weightxreps_id = {mapping.weightxreps_id}")
    if mapping.create_if_missing:
        lines.append("create_if_missing = true")

    lines.append("aliases = [")
    lines.extend(f"  {_toml_string(alias)}," for alias in _sorted_unique(mapping.aliases))
    lines.append("]")
    return "\n".join(lines)


def _sorted_unique(values: list[str]) -> list[str]:
    unique: dict[str, str] = {}
    for value in values:
        unique.setdefault(value.casefold(), value)
    return sorted(unique.values(), key=str.casefold)


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


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
