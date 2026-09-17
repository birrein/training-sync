"""Provider-neutral, source-independent planned workout definitions.

The module intentionally knows nothing about Garmin, Obsidian, or any other
destination.  It accepts the small JSON contract prepared by the assistant,
normalizes it into immutable domain objects, and produces a canonical
execution representation for previews and idempotency keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from typing import Any


SUPPORTED_SCHEMA_VERSION = 1
SUPPORTED_SPORTS = {"strength_training", "cycling", "running"}
SUPPORTED_CONTEXTS = {"indoor", "outdoor"}
SUPPORTED_ROLES = {"warmup", "work", "recovery", "cooldown", "other"}
# This is a safety bound for source expansion, not a Garmin DTO/device limit.
MAX_EXPANDED_STRENGTH_SETS = 1000


class PlannedWorkoutValidationError(ValueError):
    """Raised when a planned workout does not satisfy the input contract."""


@dataclass(frozen=True)
class Termination:
    """How an active or rest step ends."""

    until: str
    value: float | None
    unit: str | None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"until": self.until}
        if self.until == "time" and self.value is not None:
            result["seconds"] = self.value
        elif self.until == "distance" and self.value is not None:
            result["meters"] = self.value
        return result


@dataclass(frozen=True)
class LoadSpec:
    """Explicit load semantics for a strength set."""

    kind: str
    kg: float | None = None
    basis: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind}
        if self.kg is not None:
            result["kg"] = self.kg
        if self.basis is not None:
            result["basis"] = self.basis
        return result


@dataclass(frozen=True)
class TargetSpec:
    """An intensity target kept separate from step termination."""

    kind: str
    unit: str
    lower: float
    upper: float

    def to_dict(self) -> dict[str, Any]:
        value: float | dict[str, float]
        if self.lower == self.upper:
            value = self.lower
        else:
            value = {"min": self.lower, "max": self.upper}
        return {"kind": self.kind, self.unit: value}


@dataclass(frozen=True)
class PlannedSet:
    """One strength set."""

    reps: int | None
    termination: Termination
    load: LoadSpec
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"load": self.load.to_dict()}
        if self.reps is not None:
            # Keep the external contract's mutually exclusive reps/termination
            # fields round-trippable.  The normalized object retains the
            # derived reps termination internally for adapter compilation.
            result["reps"] = self.reps
        else:
            result["termination"] = self.termination.to_dict()
        if self.description is not None:
            result["description"] = self.description
        return result


@dataclass(frozen=True)
class PlannedExercise:
    """A strength exercise and its ordered sets."""

    name: str
    sets: tuple[PlannedSet, ...]
    garmin_name: str | None = None
    rest_between_sets: Termination | None = None
    rest_after_exercise: Termination | None = None
    sides: tuple[str, ...] = ()
    rest_between_sides: Termination | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "sets": [item.to_dict() for item in self.sets],
            "rest_between_sets": (
                self.rest_between_sets.to_dict() if self.rest_between_sets else None
            ),
            "rest_after_exercise": (
                self.rest_after_exercise.to_dict() if self.rest_after_exercise else None
            ),
        }
        if self.garmin_name is not None:
            result["garmin_name"] = self.garmin_name
        if self.sides:
            result["sides"] = list(self.sides)
            result["rest_between_sides"] = (
                self.rest_between_sides.to_dict() if self.rest_between_sides else None
            )
        if self.description is not None:
            result["description"] = self.description
        return result


@dataclass(frozen=True)
class PlannedStep:
    """One endurance step."""

    termination: Termination
    role: str = "work"
    target: TargetSpec | None = None
    label: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "role": self.role,
            "termination": self.termination.to_dict(),
        }
        if self.target is not None:
            result["target"] = self.target.to_dict()
        if self.label is not None:
            result["label"] = self.label
        if self.description is not None:
            result["description"] = self.description
        return result


@dataclass(frozen=True)
class PlannedBlock:
    """An ordered block, optionally repeated during compilation."""

    role: str
    steps: tuple[PlannedStep, ...]
    repeat: int = 1
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "role": self.role,
            "steps": [item.to_dict() for item in self.steps],
        }
        if self.repeat != 1:
            result["repeat"] = self.repeat
        if self.description is not None:
            result["description"] = self.description
        return result


@dataclass(frozen=True)
class PlannedWorkout:
    """Normalized workout independent of its source and destination."""

    schema_version: int
    key: str
    name: str
    sport: str
    context: str | None = None
    date: str | None = None
    warmup: PlannedStep | None = None
    exercises: tuple[PlannedExercise, ...] = ()
    blocks: tuple[PlannedBlock, ...] = ()
    provenance: Any = None

    def execution_dict(self) -> dict[str, Any]:
        """Return the canonical representation excluding provenance."""
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "key": self.key,
            "name": self.name,
            "sport": self.sport,
        }
        if self.context is not None:
            result["context"] = self.context
        if self.date is not None:
            result["date"] = self.date
        if self.warmup is not None:
            result["warmup"] = self.warmup.to_dict()
        if self.exercises:
            result["exercises"] = [item.to_dict() for item in self.exercises]
        if self.blocks:
            result["blocks"] = [item.to_dict() for item in self.blocks]
        return result

    def to_dict(self) -> dict[str, Any]:
        result = self.execution_dict()
        if self.provenance is not None:
            result["provenance"] = self.provenance
        return result

    def execution_hash(self) -> str:
        encoded = json.dumps(
            self.execution_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def planned_workout_from_dict(data: dict[str, Any]) -> PlannedWorkout:
    """Validate and normalize one versioned planned-workout document."""
    root = _object(data, "plan")
    _fields(
        root,
        {
            "schema_version",
            "key",
            "name",
            "sport",
            "context",
            "indoor",
            "date",
            "warmup",
            "exercises",
            "blocks",
            "provenance",
        },
        "plan",
        required={"schema_version", "key", "name", "sport"},
    )

    version = root["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != SUPPORTED_SCHEMA_VERSION:
        raise PlannedWorkoutValidationError(
            f"schema_version must be {SUPPORTED_SCHEMA_VERSION} at plan.schema_version"
        )

    key = _text(root["key"], "key")
    name = _text(root["name"], "name")
    sport = _text(root["sport"], "sport")
    if sport not in SUPPORTED_SPORTS:
        raise PlannedWorkoutValidationError(
            f"unsupported sport '{sport}' at plan.sport"
        )

    context = _parse_context(root)
    plan_date = _optional_date(root.get("date"))
    warmup = _parse_warmup(root.get("warmup")) if "warmup" in root else None

    exercises: tuple[PlannedExercise, ...] = ()
    blocks: tuple[PlannedBlock, ...] = ()
    if sport == "strength_training":
        if "blocks" in root:
            raise PlannedWorkoutValidationError(
                "blocks is only valid for cycling or running at plan.blocks"
            )
        exercises = _parse_exercises(root.get("exercises"), "exercises")
    else:
        if "exercises" in root:
            raise PlannedWorkoutValidationError(
                "exercises is only valid for strength_training at plan.exercises"
            )
        blocks = _parse_blocks(root.get("blocks"), sport)
        if not blocks:
            raise PlannedWorkoutValidationError("blocks must not be empty at plan.blocks")

    return PlannedWorkout(
        schema_version=version,
        key=key,
        name=name,
        sport=sport,
        context=context,
        date=plan_date,
        warmup=warmup,
        exercises=exercises,
        blocks=blocks,
        provenance=root.get("provenance"),
    )


def parse_planned_workout(data: dict[str, Any]) -> PlannedWorkout:
    """Alias for callers that prefer a parser-style name."""
    return planned_workout_from_dict(data)


def _parse_context(root: dict[str, Any]) -> str | None:
    context = root.get("context")
    indoor = root.get("indoor")
    if context is not None:
        context = _text(context, "context")
        if context not in SUPPORTED_CONTEXTS:
            raise PlannedWorkoutValidationError(
                f"unsupported context '{context}' at plan.context"
            )
    if indoor is not None:
        if not isinstance(indoor, bool):
            raise PlannedWorkoutValidationError("indoor must be boolean at plan.indoor")
        derived = "indoor" if indoor else "outdoor"
        if context is not None and context != derived:
            raise PlannedWorkoutValidationError(
                "context and indoor conflict at plan.context"
            )
        context = derived
    return context


def _parse_warmup(raw: Any) -> PlannedStep:
    obj = _object(raw, "warmup")
    _fields(
        obj,
        {"until", "seconds", "meters", "description", "target"},
        "warmup",
        required={"until"},
    )
    termination = _parse_termination(
        {key: obj[key] for key in ("until", "seconds", "meters") if key in obj},
        "warmup",
        allowed={"time", "distance", "lap"},
    )
    target = _parse_target(obj.get("target"), "warmup.target", sport=None)
    return PlannedStep(
        role="warmup",
        termination=termination,
        target=target,
        description=_optional_text(obj.get("description"), "warmup.description"),
    )


def _parse_exercises(raw: Any, path: str) -> tuple[PlannedExercise, ...]:
    values = _array(raw, path)
    if not values:
        raise PlannedWorkoutValidationError(f"{path} must not be empty")
    _validate_expanded_set_bound(values, path)
    exercises: list[PlannedExercise] = []
    expanded_count = 0
    for index, value in enumerate(values):
        exercise = _parse_exercise(
            value,
            f"{path}[{index}]",
            expanded_count=expanded_count,
        )
        exercises.append(exercise)
        expanded_count += len(exercise.sets)
    return tuple(exercises)


def _validate_expanded_set_bound(values: list[Any], path: str) -> None:
    """Check the aggregate repeat count before materializing physical sets."""

    expanded_count = 0
    for exercise_index, value in enumerate(values):
        if not isinstance(value, dict) or not isinstance(value.get("sets"), list):
            continue
        for set_index, raw_set in enumerate(value["sets"]):
            if not isinstance(raw_set, dict):
                continue
            repeat = _positive_int(
                raw_set.get("repeat", 1),
                f"{path}[{exercise_index}].sets[{set_index}].repeat",
            )
            expanded_count += repeat
            if expanded_count > MAX_EXPANDED_STRENGTH_SETS:
                raise PlannedWorkoutValidationError(
                    f"expanded strength set limit of {MAX_EXPANDED_STRENGTH_SETS} "
                    f"exceeded at {path}[{exercise_index}].sets"
                )


def _parse_exercise(
    raw: Any,
    path: str,
    *,
    expanded_count: int = 0,
) -> PlannedExercise:
    obj = _object(raw, path)
    _fields(
        obj,
        {
            "name",
            "garmin_name",
            "sets",
            "rest_between_sets",
            "rest_after_exercise",
            "sides",
            "rest_between_sides",
            "description",
        },
        path,
        required={"name", "sets"},
    )
    name = _text(obj["name"], f"{path}.name")
    garmin_name = _optional_text(obj.get("garmin_name"), f"{path}.garmin_name")
    sets_raw = _array(obj["sets"], f"{path}.sets")
    if not sets_raw:
        raise PlannedWorkoutValidationError(f"{path}.sets must not be empty")
    parsed_sets = tuple(
        _parse_set(value, f"{path}.sets[{index}]")
        for index, value in enumerate(sets_raw)
    )
    exercise_expanded_count = sum(repeat for _, repeat in parsed_sets)
    if expanded_count + exercise_expanded_count > MAX_EXPANDED_STRENGTH_SETS:
        raise PlannedWorkoutValidationError(
            f"expanded strength set limit of {MAX_EXPANDED_STRENGTH_SETS} "
            f"exceeded at {path}.sets"
        )
    sets = tuple(
        planned_set
        for planned_set, repeat in parsed_sets
        for _ in range(repeat)
    )

    rest_between_sets = _parse_rest_field(
        obj, "rest_between_sets", f"{path}.rest_between_sets"
    )
    rest_after_exercise = _parse_rest_field(
        obj, "rest_after_exercise", f"{path}.rest_after_exercise"
    )
    sides = _parse_sides(obj.get("sides"), f"{path}.sides")
    rest_between_sides = _parse_rest_field(
        obj, "rest_between_sides", f"{path}.rest_between_sides"
    )
    if sides and rest_between_sides is None and "rest_between_sides" not in obj:
        raise PlannedWorkoutValidationError(
            f"rest_between_sides is required when sides are separate at {path}.rest_between_sides"
        )
    if not sides and "rest_between_sides" in obj:
        raise PlannedWorkoutValidationError(
            f"rest_between_sides requires explicit sides at {path}.rest_between_sides"
        )

    return PlannedExercise(
        name=name,
        garmin_name=garmin_name,
        sets=sets,
        rest_between_sets=rest_between_sets,
        rest_after_exercise=rest_after_exercise,
        sides=sides,
        rest_between_sides=rest_between_sides,
        description=_optional_text(obj.get("description"), f"{path}.description"),
    )


def _parse_set(raw: Any, path: str) -> tuple[PlannedSet, int]:
    obj = _object(raw, path)
    _fields(
        obj,
        {"reps", "termination", "load", "description", "repeat"},
        path,
        required={"load"},
    )
    repeat = _positive_int(obj.get("repeat", 1), f"{path}.repeat")
    has_reps = "reps" in obj
    has_termination = "termination" in obj
    if has_reps == has_termination:
        raise PlannedWorkoutValidationError(
            f"set must provide exactly one of reps or termination at {path}.termination"
        )

    reps: int | None = None
    if has_reps:
        reps = _positive_int(obj["reps"], f"{path}.reps")
        termination = Termination("reps", float(reps), "repetitions")
    else:
        termination = _parse_termination(
            _object(obj["termination"], f"{path}.termination"),
            f"{path}.termination",
            allowed={"time", "lap"},
        )

    load = _parse_load(obj["load"], f"{path}.load")
    return (
        PlannedSet(
            reps=reps,
            termination=termination,
            load=load,
            description=_optional_text(obj.get("description"), f"{path}.description"),
        ),
        repeat,
    )


def _parse_load(raw: Any, path: str) -> LoadSpec:
    obj = _object(raw, path)
    _fields(obj, {"kind", "kg", "basis"}, path, required={"kind"})
    kind = _text(obj["kind"], f"{path}.kind")
    if kind == "bodyweight":
        if "kg" in obj or "basis" in obj:
            raise PlannedWorkoutValidationError(
                f"bodyweight load cannot include kg or basis at {path}"
            )
        return LoadSpec(kind="bodyweight")
    if kind != "mass":
        raise PlannedWorkoutValidationError(f"unsupported load kind '{kind}' at {path}.kind")
    if "kg" not in obj:
        raise PlannedWorkoutValidationError(f"kg is required for mass load at {path}.kg")
    if "basis" not in obj:
        raise PlannedWorkoutValidationError(f"basis is required for mass load at {path}.basis")
    kg = _nonnegative_number(obj["kg"], f"{path}.kg")
    basis = _text(obj["basis"], f"{path}.basis")
    if basis not in {"total", "per_hand"}:
        raise PlannedWorkoutValidationError(
            f"unsupported load basis '{basis}' at {path}.basis"
        )
    return LoadSpec(kind=kind, kg=kg, basis=basis)


def _parse_sides(raw: Any, path: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    values = _array(raw, path)
    if [value for value in values if not isinstance(value, str)] or len(values) != 2:
        raise PlannedWorkoutValidationError(
            f"sides must be exactly ['left', 'right'] at {path}"
        )
    normalized = tuple(value.lower() for value in values)
    if normalized != ("left", "right"):
        raise PlannedWorkoutValidationError(
            f"sides must be exactly ['left', 'right'] at {path}"
        )
    return normalized


def _parse_rest_field(
    obj: dict[str, Any], key: str, path: str
) -> Termination | None:
    if key not in obj or obj[key] is None:
        return None
    value = _object(obj[key], path)
    return _parse_termination(value, path, allowed={"time", "lap"})


def _parse_termination(
    obj: dict[str, Any], path: str, *, allowed: set[str]
) -> Termination:
    _fields(obj, {"until", "seconds", "meters"}, path, required={"until"})
    until = _text(obj["until"], f"{path}.until")
    if until not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise PlannedWorkoutValidationError(
            f"unsupported termination '{until}' at {path}.until; expected {allowed_text}"
        )
    if until == "lap":
        if "seconds" in obj or "meters" in obj:
            raise PlannedWorkoutValidationError(
                f"lap termination cannot include a numeric value at {path}"
            )
        return Termination(until="lap", value=None, unit=None)
    if until == "time":
        if "meters" in obj or "seconds" not in obj:
            raise PlannedWorkoutValidationError(
                f"time termination requires seconds only at {path}.seconds"
            )
        return Termination(
            until="time",
            value=_positive_number(obj["seconds"], f"{path}.seconds"),
            unit="seconds",
        )
    if "seconds" in obj or "meters" not in obj:
        raise PlannedWorkoutValidationError(
            f"distance termination requires meters only at {path}.meters"
        )
    return Termination(
        until="distance",
        value=_positive_number(obj["meters"], f"{path}.meters"),
        unit="meters",
    )


def _parse_blocks(raw: Any, sport: str) -> tuple[PlannedBlock, ...]:
    values = _array(raw, "blocks")
    if not values:
        raise PlannedWorkoutValidationError("blocks must not be empty at blocks")
    return tuple(
        _parse_block(value, f"blocks[{index}]", sport)
        for index, value in enumerate(values)
    )


def _parse_block(raw: Any, path: str, sport: str) -> PlannedBlock:
    obj = _object(raw, path)
    _fields(obj, {"role", "repeat", "steps", "description"}, path, required={"role", "steps"})
    role = _text(obj["role"], f"{path}.role")
    if role not in SUPPORTED_ROLES:
        raise PlannedWorkoutValidationError(f"unsupported block role '{role}' at {path}.role")
    repeat = _positive_int(obj.get("repeat", 1), f"{path}.repeat")
    values = _array(obj["steps"], f"{path}.steps")
    if not values:
        raise PlannedWorkoutValidationError(f"{path}.steps must not be empty")
    steps = tuple(
        _parse_step(value, f"{path}.steps[{index}]", sport, default_role=role)
        for index, value in enumerate(values)
    )
    return PlannedBlock(
        role=role,
        steps=steps,
        repeat=repeat,
        description=_optional_text(obj.get("description"), f"{path}.description"),
    )


def _parse_step(raw: Any, path: str, sport: str, *, default_role: str) -> PlannedStep:
    obj = _object(raw, path)
    _fields(
        obj,
        {"role", "label", "termination", "target", "description"},
        path,
        required={"termination"},
    )
    role = _text(obj.get("role", default_role), f"{path}.role")
    if role not in SUPPORTED_ROLES:
        raise PlannedWorkoutValidationError(f"unsupported step role '{role}' at {path}.role")
    termination = _parse_termination(
        _object(obj["termination"], f"{path}.termination"),
        f"{path}.termination",
        allowed={"time", "distance", "lap"},
    )
    target = _parse_target(obj.get("target"), f"{path}.target", sport=sport)
    return PlannedStep(
        role=role,
        label=_optional_text(obj.get("label"), f"{path}.label"),
        termination=termination,
        target=target,
        description=_optional_text(obj.get("description"), f"{path}.description"),
    )


def _parse_target(raw: Any, path: str, sport: str | None) -> TargetSpec | None:
    if raw is None:
        return None
    obj = _object(raw, path)
    _fields(
        obj,
        {"kind", "watts", "seconds_per_km", "bpm", "rpm", "reference"},
        path,
        required={"kind"},
    )
    kind = _text(obj["kind"], f"{path}.kind")
    field_by_kind = {
        "power": "watts",
        "pace": "seconds_per_km",
        "heart_rate": "bpm",
        "cadence": "rpm",
    }
    if kind not in field_by_kind:
        raise PlannedWorkoutValidationError(f"unsupported target kind '{kind}' at {path}.kind")
    if "reference" in obj:
        reference = _text(obj["reference"], f"{path}.reference")
        raise PlannedWorkoutValidationError(
            f"target reference '{reference}' requires a supported threshold mapping at {path}.reference"
        )
    field = field_by_kind[kind]
    if field not in obj:
        raise PlannedWorkoutValidationError(f"{field} is required at {path}.{field}")
    other_fields = set(obj) - {"kind", field}
    if other_fields:
        # `_fields` already catches unknown keys; this catches a known target
        # unit supplied for the wrong target kind.
        other = sorted(other_fields)[0]
        raise PlannedWorkoutValidationError(
            f"target field '{other}' is incompatible with {kind} at {path}.{other}"
        )
    lower, upper = _parse_bounds(obj[field], f"{path}.{field}")
    if sport == "running" and kind == "cadence":
        raise PlannedWorkoutValidationError(
            f"cadence targets are only supported for cycling at {path}.kind"
        )
    if sport == "cycling" and kind == "pace":
        raise PlannedWorkoutValidationError(
            f"pace targets are only supported for running at {path}.kind"
        )
    return TargetSpec(kind=kind, unit=field, lower=lower, upper=upper)


def _parse_bounds(raw: Any, path: str) -> tuple[float, float]:
    if isinstance(raw, bool):
        raise PlannedWorkoutValidationError(f"numeric target required at {path}")
    if isinstance(raw, (int, float)):
        value = _positive_number(raw, path)
        return value, value
    obj = _object(raw, path)
    _fields(obj, {"min", "max"}, path, required={"min", "max"})
    lower = _positive_number(obj["min"], f"{path}.min")
    upper = _positive_number(obj["max"], f"{path}.max")
    if lower > upper:
        raise PlannedWorkoutValidationError(f"target range is inverted at {path}")
    return lower, upper


def _optional_date(raw: Any) -> str | None:
    if raw is None:
        return None
    value = _text(raw, "date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise PlannedWorkoutValidationError(f"invalid ISO date at date") from exc
    return value


def _fields(
    obj: dict[str, Any], allowed: set[str], path: str, *, required: set[str] | None = None
) -> None:
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise PlannedWorkoutValidationError(f"unknown field '{unknown[0]}' at {path}")
    missing = sorted((required or set()) - set(obj))
    if missing:
        raise PlannedWorkoutValidationError(f"missing field '{missing[0]}' at {path}")


def _object(raw: Any, path: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PlannedWorkoutValidationError(f"expected object at {path}")
    return raw


def _array(raw: Any, path: str) -> list[Any]:
    if not isinstance(raw, list):
        raise PlannedWorkoutValidationError(f"expected array at {path}")
    return raw


def _text(raw: Any, path: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise PlannedWorkoutValidationError(f"expected non-empty string at {path}")
    return raw.strip()


def _optional_text(raw: Any, path: str) -> str | None:
    if raw is None:
        return None
    return _text(raw, path)


def _positive_int(raw: Any, path: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        raise PlannedWorkoutValidationError(f"expected positive integer at {path}")
    return raw


def _positive_number(raw: Any, path: str) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise PlannedWorkoutValidationError(f"expected positive finite number at {path}")
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        raise PlannedWorkoutValidationError(f"expected positive finite number at {path}")
    return value


def _nonnegative_number(raw: Any, path: str) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise PlannedWorkoutValidationError(f"expected nonnegative finite number at {path}")
    value = float(raw)
    if not math.isfinite(value) or value < 0:
        raise PlannedWorkoutValidationError(f"expected nonnegative finite number at {path}")
    return value
