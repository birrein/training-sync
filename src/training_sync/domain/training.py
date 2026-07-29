"""Provider-neutral values for completed training activities.

These values deliberately carry only stable cross-provider concepts.  Provider
payloads and dense telemetry stay in their adapters or ``SourceArtifact``.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Mapping


class LoadKind(StrEnum):
    MASS = "mass"
    BODYWEIGHT = "bodyweight"
    ASSISTANCE = "assistance"
    RESISTANCE = "resistance"
    NONE = "none"


class EffortScope(StrEnum):
    SET = "set"
    EXERCISE = "exercise"
    SESSION = "session"


@dataclass(frozen=True)
class Provenance:
    provider: str
    reference: str
    verified: bool = False
    derived_from: str | None = None


@dataclass(frozen=True)
class SourceArtifact:
    """Opaque source-file or provider-payload reference.

    ``reference`` is intentionally a locator, not the decoded provider payload.
    """

    kind: str
    reference: str
    content_type: str | None = None


@dataclass(frozen=True)
class Load:
    kind: LoadKind
    value: float | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        if self.kind is LoadKind.NONE:
            if self.value is not None or self.unit is not None:
                raise ValueError("A no-load set cannot include a value or unit")
        elif self.kind is LoadKind.BODYWEIGHT:
            if self.value is not None:
                raise ValueError("A bodyweight load cannot include a mass value")
        elif self.value is None:
            raise ValueError(f"{self.kind} load requires a value")

    @classmethod
    def bodyweight(cls) -> "Load":
        return cls(kind=LoadKind.BODYWEIGHT)

    @classmethod
    def none(cls) -> "Load":
        return cls(kind=LoadKind.NONE)


@dataclass(frozen=True)
class StrengthSet:
    order: int
    role: str
    reps: int | None
    load: Load


@dataclass(frozen=True)
class StrengthExercise:
    key: str
    name: str
    order: int
    sets: tuple[StrengthSet, ...]


@dataclass(frozen=True)
class StrengthWorkout:
    exercises: tuple[StrengthExercise, ...]


@dataclass(frozen=True)
class StrengthWorkoutImport:
    """Extracted strength evidence; it is not a completed activity."""

    date: str
    workout: StrengthWorkout
    provenance: Provenance
    title: str | None = None


@dataclass(frozen=True)
class EffortObservation:
    metric: str
    value: float
    scope: EffortScope
    provenance: Provenance
    exercise_key: str | None = None
    set_order: int | None = None

    def __post_init__(self) -> None:
        if self.scope is EffortScope.SESSION and (
            self.exercise_key is not None or self.set_order is not None
        ):
            raise ValueError("Session effort cannot identify an exercise or set")
        if self.scope is EffortScope.EXERCISE and self.exercise_key is None:
            raise ValueError("Exercise effort requires exercise_key")
        if self.scope is EffortScope.SET and (
            self.exercise_key is None or self.set_order is None
        ):
            raise ValueError("Set effort requires exercise_key and set_order")


@dataclass(frozen=True)
class CompletedActivity:
    key: str
    title: str
    activity_type: str
    local_start: datetime
    elapsed_duration_s: float
    active_duration_s: float | None
    provenance: Provenance
    objective_summary: Mapping[str, float | int | str] = field(default_factory=dict)
    strength: StrengthWorkout | None = None
    effort: tuple[EffortObservation, ...] = ()
    source_artifacts: tuple[SourceArtifact, ...] = ()
