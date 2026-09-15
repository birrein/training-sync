"""Compile provider-neutral planned workouts into Garmin workout DTOs.

This module is deliberately an adapter boundary.  It consumes the validated
domain model, reuses the existing Garmin exercise mapping, and produces a
deterministic flat sequence suitable for preview and later publication.  It
does not authenticate, call Garmin, read the vault, or mutate any local
training record.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from training_sync.domain.exercise_catalog import normalize_exercise_identity
from training_sync.domain.planned_workout import (
    LoadSpec,
    PlannedBlock,
    PlannedExercise,
    PlannedSet,
    PlannedStep,
    PlannedWorkout,
    TargetSpec,
    Termination,
    planned_workout_from_dict,
)
from training_sync.garmin.exercise_mapping import (
    FITBOD_CUSTOM_MAP,
    get_mapping,
    load_garmin_dict,
)


GRAMS_PER_KG = 1000.0


class ExerciseResolutionError(ValueError):
    """Raised when an exercise cannot be assigned one Garmin identity."""


class ExerciseResolutionConflictError(ExerciseResolutionError):
    """Raised when a normalized exercise label has incompatible mappings."""


class ProviderStepLimitError(ValueError):
    """Raised when a provider limit would require silently truncating steps."""


@dataclass(frozen=True)
class ExerciseResolution:
    """The selected Garmin identity and the reason it won."""

    original_name: str
    selected_name: str
    mapping: dict[str, Any]
    source: str


@dataclass(frozen=True)
class GarminWorkoutProjection:
    """A deterministic payload plus the exact steps shown in preview."""

    payload: dict[str, Any]
    steps: tuple[dict[str, Any], ...]
    preview: str
    resolutions: tuple[ExerciseResolution, ...] = ()


_SPORT_TYPES: dict[str, dict[str, Any]] = {
    "running": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
    "cycling": {"sportTypeId": 2, "sportTypeKey": "cycling", "displayOrder": 2},
    "strength_training": {
        "sportTypeId": 5,
        "sportTypeKey": "strength_training",
        "displayOrder": 5,
    },
}

_STEP_TYPES: dict[str, dict[str, Any]] = {
    "warmup": {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
    "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
    "interval": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
    "recovery": {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
    "rest": {"stepTypeId": 5, "stepTypeKey": "rest", "displayOrder": 5},
    "other": {"stepTypeId": 7, "stepTypeKey": "other", "displayOrder": 7},
}

_CONDITIONS: dict[str, dict[str, Any]] = {
    "lap": {
        "conditionTypeId": 1,
        "conditionTypeKey": "lap.button",
        "displayOrder": 1,
        "displayable": True,
    },
    "time": {
        "conditionTypeId": 2,
        "conditionTypeKey": "time",
        "displayOrder": 2,
        "displayable": True,
    },
    "distance": {
        "conditionTypeId": 3,
        "conditionTypeKey": "distance",
        "displayOrder": 3,
        "displayable": True,
    },
    "reps": {
        "conditionTypeId": 10,
        "conditionTypeKey": "reps",
        "displayOrder": 10,
        "displayable": True,
    },
}

_TARGETS: dict[str, dict[str, Any]] = {
    "none": {
        "workoutTargetTypeId": 1,
        "workoutTargetTypeKey": "no.target",
        "displayOrder": 1,
    },
    "power": {
        "workoutTargetTypeId": 9,
        "workoutTargetTypeKey": "power.lap",
        "displayOrder": 9,
    },
    "pace": {
        "workoutTargetTypeId": 6,
        "workoutTargetTypeKey": "pace.zone",
        "displayOrder": 6,
    },
    "heart_rate": {
        "workoutTargetTypeId": 4,
        "workoutTargetTypeKey": "heart.rate.zone",
        "displayOrder": 4,
    },
    "cadence": {
        "workoutTargetTypeId": 3,
        "workoutTargetTypeKey": "cadence",
        "displayOrder": 3,
    },
}


def resolve_garmin_exercise(
    name: str,
    *,
    garmin_name: str | None = None,
    garmin_dict: Mapping[str, Mapping[str, Any]] | None = None,
) -> ExerciseResolution:
    """Resolve one exercise using the planned-workout precedence contract.

    The order is intentionally visible in this function:

    1. an explicit, user-authorized ``garmin_name`` is resolved against the
       catalog and bypasses generic mappings;
    2. the existing custom Garmin mapping (including its aliases) wins;
    3. a normalized exact catalog label is used.

    Fuzzy matching and automatic substitutions are not part of planned
    publication.  A normalized catalog collision is accepted only when all
    candidates describe the same provider identity.
    """

    catalog = garmin_dict if garmin_dict is not None else load_garmin_dict()
    if garmin_name is not None:
        mapping = _resolve_catalog_label(garmin_name, catalog)
        return ExerciseResolution(name, garmin_name, mapping, "explicit_garmin_name")

    custom = _resolve_custom_mapping(name)
    if custom is not None:
        return ExerciseResolution(name, name, custom, "existing_mapping")

    # Keep the established adapter behavior in the normal exact-name path.
    # We still inspect normalized candidates below so punctuation and case do
    # not create a false unresolved result and catalog collisions are visible.
    legacy_mapping = get_mapping(name, dict(catalog))
    if legacy_mapping.get("category") != "UNKNOWN":
        candidates = _catalog_candidates(name, catalog)
        if candidates:
            mapping = _unique_mapping(candidates, name)
            return ExerciseResolution(name, name, mapping, "catalog")
        return ExerciseResolution(name, name, _without_probability(legacy_mapping), "catalog")

    candidates = _catalog_candidates(name, catalog)
    if not candidates:
        raise ExerciseResolutionError(
            f"Exercise '{name}' has no unambiguous Garmin mapping; "
            "provide an explicit garmin_name if a substitute is intended"
        )
    return ExerciseResolution(name, name, _unique_mapping(candidates, name), "catalog")


def project_planned_workout(
    workout: PlannedWorkout | Mapping[str, Any],
    *,
    garmin_dict: Mapping[str, Mapping[str, Any]] | None = None,
    max_steps: int | None = None,
) -> GarminWorkoutProjection:
    """Compile a validated plan without authentication or network I/O."""

    if isinstance(workout, Mapping):
        workout = planned_workout_from_dict(dict(workout))
    if workout.sport not in _SPORT_TYPES:
        raise ValueError(f"unsupported Garmin sport '{workout.sport}'")

    catalog = garmin_dict if garmin_dict is not None else load_garmin_dict()
    raw_steps: list[dict[str, Any]] = []
    resolutions: list[ExerciseResolution] = []

    if workout.sport == "strength_training":
        if workout.warmup is not None:
            raw_steps.append(
                _endurance_step(
                    workout.warmup,
                    order=0,
                    step_type=workout.warmup.role,
                    description=workout.warmup.description or "Warm-up",
                )
            )
        for index, exercise in enumerate(workout.exercises):
            resolution = resolve_garmin_exercise(
                exercise.name,
                garmin_name=exercise.garmin_name,
                garmin_dict=catalog,
            )
            resolutions.append(resolution)
            next_name = (
                workout.exercises[index + 1].name
                if index + 1 < len(workout.exercises)
                else None
            )
            _append_strength_exercise(
                raw_steps,
                exercise,
                resolution,
                next_name=next_name,
            )
    else:
        if workout.warmup is not None:
            raw_steps.append(
                _endurance_step(
                    workout.warmup,
                    order=0,
                    step_type="warmup",
                    description=workout.warmup.description or "Warm-up",
                )
            )
        for block in workout.blocks:
            for _ in range(block.repeat):
                for step in block.steps:
                    description = _endurance_description(step, block)
                    raw_steps.append(
                        _endurance_step(
                            step,
                            order=0,
                            step_type=_step_type_for_role(step.role),
                            description=description,
                        )
                    )

    if max_steps is not None and len(raw_steps) > max_steps:
        raise ProviderStepLimitError(
            f"Garmin provider step limit {max_steps} exceeded by "
            f"complete plan ({len(raw_steps)} steps); no steps were truncated"
        )

    steps = tuple(_reorder_steps(raw_steps))
    sport_type = dict(_SPORT_TYPES[workout.sport])
    description = _workout_description(workout)
    payload: dict[str, Any] = {
        "workoutName": workout.name,
        "sportType": sport_type,
        "estimatedDurationInSecs": _estimated_duration(steps),
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": dict(sport_type),
                "workoutSteps": [dict(step) for step in steps],
            }
        ],
        "description": description,
    }
    if workout.context is not None:
        # Garmin has no portable "indoor" boolean in the workout DTO.  Keep
        # it visible in the provider description so the distinction is not
        # silently lost; actual device interpretation remains unverified.
        payload["context"] = workout.context
    return GarminWorkoutProjection(
        payload=payload,
        steps=steps,
        preview=_preview(workout, steps, resolutions),
        resolutions=tuple(resolutions),
    )


def build_garmin_workout_payload(
    workout: PlannedWorkout,
    *,
    garmin_dict: Mapping[str, Mapping[str, Any]] | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    """Compatibility helper returning only the projected Garmin payload."""

    return project_planned_workout(
        workout, garmin_dict=garmin_dict, max_steps=max_steps
    ).payload


def flatten_planned_workout(
    workout: PlannedWorkout,
    *,
    garmin_dict: Mapping[str, Mapping[str, Any]] | None = None,
    max_steps: int | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return the exact flat executable sequence used by the projection."""

    return project_planned_workout(
        workout, garmin_dict=garmin_dict, max_steps=max_steps
    ).steps


def _append_strength_exercise(
    target: list[dict[str, Any]],
    exercise: PlannedExercise,
    resolution: ExerciseResolution,
    *,
    next_name: str | None,
) -> None:
    separate_sides = bool(exercise.sides)
    for set_index, planned_set in enumerate(exercise.sets):
        if separate_sides:
            for side_index, side in enumerate(exercise.sides):
                target.append(
                    _strength_step(
                        planned_set,
                        exercise,
                        resolution,
                        order=0,
                        side=side,
                        both_sides=False,
                    )
                )
                if side_index + 1 < len(exercise.sides):
                    if exercise.rest_between_sides is not None:
                        target.append(
                            _rest_step(
                                exercise.rest_between_sides,
                                order=0,
                                description=(
                                    f"Rest {_format_number(exercise.rest_between_sides.value)} "
                                    f"seconds between sides of {exercise.name}"
                                    if exercise.rest_between_sides.until == "time"
                                    else f"Manual rest between sides of {exercise.name}"
                                ),
                            )
                        )
            rest = (
                exercise.rest_between_sets
                if set_index + 1 < len(exercise.sets)
                else exercise.rest_after_exercise
            )
            if rest is not None:
                target.append(
                    _rest_step(
                        rest,
                        order=0,
                        description=_rest_description(
                            rest,
                            exercise.name,
                            next_name=next_name,
                        ),
                    )
                )
            continue

        both_sides = planned_set.load.basis == "per_hand"
        target.append(
            _strength_step(
                planned_set,
                exercise,
                resolution,
                order=0,
                side="both" if both_sides else None,
                both_sides=both_sides,
            )
        )
        rest = (
            exercise.rest_between_sets
            if set_index + 1 < len(exercise.sets)
            else exercise.rest_after_exercise
        )
        if rest is not None:
            target.append(
                _rest_step(
                    rest,
                    order=0,
                    description=_rest_description(
                        rest,
                        exercise.name,
                        next_name=next_name,
                    ),
                )
            )


def _strength_step(
    planned_set: PlannedSet,
    exercise: PlannedExercise,
    resolution: ExerciseResolution,
    *,
    order: int,
    side: str | None,
    both_sides: bool,
) -> dict[str, Any]:
    termination = planned_set.termination
    mapping = resolution.mapping
    description_parts = [exercise.name]
    if resolution.source == "explicit_garmin_name":
        description_parts.append(f"(Garmin: {resolution.selected_name})")
    if planned_set.description:
        description_parts.append(planned_set.description)
    if exercise.description:
        description_parts.append(exercise.description)
    description_parts.append(_load_description(planned_set.load))
    description_parts.append(_termination_description(termination))
    if side is not None and side != "both":
        description_parts.append(f"{side} side")
    elif both_sides:
        description_parts.append("complete both sides before ending the set")

    step = _base_step(
        order=order,
        step_type="interval",
        termination=termination,
        description="; ".join(part for part in description_parts if part),
    )
    step.update(
        {
            "category": mapping.get("category"),
            "exerciseName": mapping.get("name"),
            "originalExerciseName": exercise.name,
            "garminName": resolution.selected_name,
            "repetitionCount": (
                int(termination.value)
                if termination.until == "reps" and termination.value is not None
                else None
            ),
            "weightValue": _weight_value(planned_set.load),
            "weightUnit": "gram" if planned_set.load.kind == "mass" else None,
            "weightBasis": planned_set.load.basis,
            "loadKind": planned_set.load.kind,
        }
    )
    if side is not None:
        step["side"] = side
    return step


def _rest_step(
    termination: Termination,
    *,
    order: int,
    description: str,
) -> dict[str, Any]:
    step = _base_step(
        order=order,
        step_type="rest",
        termination=termination,
        description=description,
    )
    step.update(
        {
            "category": None,
            "exerciseName": None,
            "weightValue": None,
            "weightUnit": None,
            "weightBasis": None,
            "loadKind": None,
        }
    )
    return step


def _endurance_step(
    planned_step: PlannedStep,
    *,
    order: int,
    step_type: str,
    description: str,
) -> dict[str, Any]:
    step = _base_step(
        order=order,
        step_type=step_type,
        termination=planned_step.termination,
        description=description,
        target=planned_step.target,
    )
    step.update(
        {
            "category": "CARDIO",
            "exerciseName": None,
            "originalExerciseName": None,
            "garminName": None,
            "repetitionCount": None,
            "weightValue": None,
            "weightUnit": None,
            "weightBasis": None,
            "loadKind": None,
        }
    )
    return step


def _base_step(
    *,
    order: int,
    step_type: str,
    termination: Termination,
    description: str,
    target: TargetSpec | None = None,
) -> dict[str, Any]:
    if step_type not in _STEP_TYPES:
        raise ValueError(f"unsupported Garmin step role '{step_type}'")
    condition = dict(_CONDITIONS[termination.until])
    target_data = _target_data(target)
    return {
        "type": "ExecutableStepDTO",
        "stepOrder": order,
        "stepType": dict(_STEP_TYPES[step_type]),
        "childStepId": None,
        "description": description,
        "endCondition": condition,
        "endConditionValue": _provider_value(termination),
        "preferredEndConditionUnit": termination.unit,
        "endConditionCompare": None,
        "targetType": target_data["targetType"],
        "targetValueOne": target_data["targetValueOne"],
        "targetValueTwo": target_data["targetValueTwo"],
        "targetValueUnit": target_data["targetValueUnit"],
    }


def _target_data(target: TargetSpec | None) -> dict[str, Any]:
    if target is None:
        return {
            "targetType": dict(_TARGETS["none"]),
            "targetValueOne": None,
            "targetValueTwo": None,
            "targetValueUnit": None,
        }
    return {
        "targetType": dict(_TARGETS[target.kind]),
        "targetValueOne": _number_or_int(target.lower),
        "targetValueTwo": _number_or_int(target.upper),
        "targetValueUnit": target.unit,
    }


def _reorder_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for order, step in enumerate(steps, start=1):
        copied = dict(step)
        copied["stepOrder"] = order
        result.append(copied)
    return result


def _resolve_custom_mapping(name: str) -> dict[str, Any] | None:
    normalized_name = _normalize_garmin_label(name)
    matches: list[dict[str, Any]] = []
    for alias, mapping in FITBOD_CUSTOM_MAP.items():
        if _normalize_garmin_label(alias) == normalized_name:
            matches.append(_without_probability(mapping))
    if not matches:
        return None
    return _unique_mapping(matches, name)


def _resolve_catalog_label(
    label: str,
    catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    candidates = _catalog_candidates(label, catalog, include_provider_names=True)
    if not candidates:
        raise ExerciseResolutionError(
            f"Explicit garmin_name '{label}' is not present in the Garmin catalog"
        )
    return _unique_mapping(candidates, label)


def _catalog_candidates(
    label: str,
    catalog: Mapping[str, Mapping[str, Any]],
    *,
    include_provider_names: bool = True,
) -> list[dict[str, Any]]:
    normalized = _normalize_garmin_label(label)
    candidates: list[dict[str, Any]] = []
    for catalog_name, raw_mapping in catalog.items():
        if not isinstance(catalog_name, str) or not isinstance(raw_mapping, Mapping):
            continue
        names = [catalog_name]
        provider_name = raw_mapping.get("name")
        if include_provider_names and isinstance(provider_name, str):
            names.append(provider_name)
        if any(_normalize_garmin_label(value) == normalized for value in names):
            candidates.append(_without_probability(raw_mapping))
    return candidates


def _unique_mapping(
    candidates: list[Mapping[str, Any]],
    label: str,
) -> dict[str, Any]:
    identities = {
        (
            _normalize_garmin_label(str(candidate.get("category", ""))),
            _normalize_garmin_label(str(candidate.get("name", ""))),
        )
        for candidate in candidates
    }
    if len(identities) != 1:
        rendered = ", ".join(
            f"{category}/{name}" for category, name in sorted(identities, key=str)
        )
        raise ExerciseResolutionConflictError(
            f"Exercise '{label}' has conflicting Garmin mappings: {rendered}"
        )
    # The catalog contains pairs such as a human label and its enum spelling.
    # They are one provider identity after normalization; prefer the enum
    # spelling because Garmin workout DTOs use that value for exerciseName.
    preferred = sorted(
        candidates,
        key=lambda candidate: (
            0
            if not _looks_like_provider_enum(candidate.get("name"))
            else -1
        ),
    )
    return dict(preferred[0])


def _looks_like_provider_enum(value: Any) -> bool:
    return isinstance(value, str) and (
        value == value.upper() or "_" in value
    )


def _normalize_garmin_label(value: str) -> str:
    """Normalize human and Garmin enum spellings to one comparison label."""

    return normalize_exercise_identity(value.replace("_", " "))


def _step_type_for_role(role: str) -> str:
    if role == "work":
        return "interval"
    return role


def _without_probability(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in mapping.items() if key != "probability"}


def _weight_value(load: LoadSpec) -> float | None:
    if load.kind == "bodyweight":
        return None
    if load.kg is None:
        raise ValueError("mass load is missing kilograms")
    return _number_or_int(load.kg * GRAMS_PER_KG)


def _provider_value(termination: Termination) -> float | int | None:
    if termination.value is None:
        return None
    return _number_or_int(termination.value)


def _number_or_int(value: float) -> float | int:
    return int(value) if float(value).is_integer() else float(value)


def _estimated_duration(steps: tuple[dict[str, Any], ...]) -> int:
    total = 0.0
    for step in steps:
        if step["endCondition"]["conditionTypeKey"] == "time":
            total += float(step["endConditionValue"] or 0)
    return max(0, int(math.ceil(total)))


def _workout_description(workout: PlannedWorkout) -> str:
    parts = [f"training-sync plan {workout.key}"]
    if workout.context:
        parts.append(f"context: {workout.context}")
    return " | ".join(parts)


def _endurance_description(step: PlannedStep, block: PlannedBlock) -> str:
    parts = [step.role]
    if step.label:
        parts.append(step.label)
    if block.description:
        parts.append(block.description)
    parts.append(_termination_description(step.termination))
    if step.target is not None:
        parts.append(_target_description(step.target))
    if step.description:
        parts.append(step.description)
    return "; ".join(parts)


def _rest_description(
    termination: Termination,
    exercise_name: str,
    *,
    next_name: str | None,
) -> str:
    if termination.until == "time":
        duration = f"{_format_number(termination.value)} seconds"
    else:
        duration = "manual lap"
    if next_name is not None:
        return f"Rest {duration} before {next_name}"
    return f"Rest {duration} after {exercise_name}"


def _termination_description(termination: Termination) -> str:
    if termination.until == "reps":
        return f"{_format_number(termination.value)} reps"
    if termination.until == "time":
        return f"{_format_number(termination.value)} seconds"
    if termination.until == "distance":
        return f"{_format_number(termination.value)} meters"
    return "manual lap"


def _load_description(load: LoadSpec) -> str:
    if load.kind == "bodyweight":
        return "bodyweight"
    assert load.kg is not None
    basis = "per hand" if load.basis == "per_hand" else "total"
    return f"{_format_number(load.kg)} kg {basis}"


def _target_description(target: TargetSpec) -> str:
    if target.lower == target.upper:
        value = _format_number(target.lower)
    else:
        value = f"{_format_number(target.lower)}-{_format_number(target.upper)}"
    return f"target {value} {target.unit}"


def _format_number(value: float | None) -> str:
    if value is None:
        return "?"
    return str(_number_or_int(float(value)))


def _preview(
    workout: PlannedWorkout,
    steps: tuple[dict[str, Any], ...],
    resolutions: list[ExerciseResolution],
) -> str:
    lines = [f"{workout.name} [{workout.sport}] — {len(steps)} steps"]
    if workout.context:
        lines.append(f"Context: {workout.context}")
    for step in steps:
        condition = step["endCondition"]["conditionTypeKey"]
        value = step["endConditionValue"]
        if condition == "lap.button":
            termination = "manual lap"
        else:
            termination = f"{_format_number(value)} {step['preferredEndConditionUnit']}"
        target = step.get("targetValueUnit")
        if target:
            lower = step.get("targetValueOne")
            upper = step.get("targetValueTwo")
            target_value = (
                _format_number(lower)
                if lower == upper
                else f"{_format_number(lower)}-{_format_number(upper)}"
            )
            target_text = f"; target {target_value} {target}"
        else:
            target_text = ""
        lines.append(
            f"{step['stepOrder']}. {step['stepType']['stepTypeKey']}: "
            f"{step['description']} [{termination}{target_text}]"
        )
    if resolutions:
        lines.append(
            "Mappings: "
            + ", ".join(
                f"{item.original_name} -> {item.mapping.get('category')}/"
                f"{item.mapping.get('name')} ({item.source})"
                for item in resolutions
            )
        )
    return "\n".join(lines)


# Names used by earlier callers while the adapter was being introduced.
build_planned_workout_payload = build_garmin_workout_payload
compile_planned_workout = project_planned_workout
