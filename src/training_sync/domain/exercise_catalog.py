"""Stable local exercise identities and provider-specific bindings."""

from dataclasses import dataclass, field
import re


def normalize_exercise_identity(value: str) -> str:
    value = re.sub(r"[^\w\s]", " ", value.strip().removeprefix("#").lower())
    return re.sub(r"\s+", " ", value).strip()


@dataclass(frozen=True)
class ProviderBinding:
    name: str
    remote_id: int | None = None
    create_if_missing: bool = False


@dataclass(frozen=True)
class ExerciseIdentity:
    key: str
    name: str
    aliases: tuple[str, ...] = ()
    providers: dict[str, ProviderBinding] = field(default_factory=dict)


@dataclass(frozen=True)
class ExerciseCatalog:
    exercises: tuple[ExerciseIdentity, ...]

    def __post_init__(self) -> None:
        seen: dict[str, str] = {}
        for exercise in self.exercises:
            for candidate in (exercise.key, exercise.name, *exercise.aliases):
                normalized = normalize_exercise_identity(candidate)
                prior = seen.get(normalized)
                if prior is not None and prior != exercise.key:
                    raise ValueError(
                        f"Duplicate exercise alias '{normalized}' maps to {prior} and {exercise.key}"
                    )
                seen[normalized] = exercise.key

    def resolve(self, name: str) -> ExerciseIdentity:
        normalized = normalize_exercise_identity(name)
        for exercise in self.exercises:
            if normalized in {
                normalize_exercise_identity(value)
                for value in (exercise.key, exercise.name, *exercise.aliases)
            }:
                return exercise
        raise KeyError(name)

    def resolve_provider(self, provider: str, remote_id: int) -> ExerciseIdentity:
        for exercise in self.exercises:
            binding = exercise.providers.get(provider)
            if binding and binding.remote_id == remote_id:
                return exercise
        raise KeyError((provider, remote_id))
