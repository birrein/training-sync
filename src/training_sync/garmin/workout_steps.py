"""Decode the supported Garmin planned-workout step tree.

Garmin may store a repeated sequence as one ``RepeatGroupDTO`` whose child
steps are executed once per iteration.  The rest of the application compares
the executable sequence, so this module is the single bounded decoder used by
publication verification and template management.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


# This bound protects callers from provider payloads that request an enormous
# expansion.  It is independent from Garmin's DTO-count/device capacity.
MAX_EXPANDED_WORKOUT_STEPS = 10_000


class WorkoutStepDecodeError(ValueError):
    """Raised when a Garmin step tree is malformed or unsupported."""


@dataclass(frozen=True)
class RepeatGroupLayout:
    """The requested/stored shape of one supported repeat group."""

    start_index: int
    iterations: int
    skip_last_rest_step: bool
    child_steps: tuple[dict[str, Any], ...]
    child_step_id: Any = None
    step_order: Any = None
    group_type: Any = None
    step_type_key: Any = None

    @property
    def expanded_step_count(self) -> int:
        count = len(self.child_steps) * self.iterations
        if self.skip_last_rest_step and self.child_steps and _is_rest_step(
            self.child_steps[-1]
        ):
            count -= 1
        return count


@dataclass(frozen=True)
class DecodedWorkoutSteps:
    """Expanded executable steps plus the repeat layouts found in the DTO."""

    steps: tuple[dict[str, Any], ...]
    repeat_groups: tuple[RepeatGroupLayout, ...] = ()

    @property
    def has_repeat_groups(self) -> bool:
        return bool(self.repeat_groups)


def decode_workout_steps(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    max_expanded_steps: int = MAX_EXPANDED_WORKOUT_STEPS,
) -> DecodedWorkoutSteps:
    """Expand a supported Garmin payload without mutating its input.

    Both the usual ``workoutSegments[*].workoutSteps`` envelope and a direct
    step sequence are accepted.  Repeat groups are deliberately limited to a
    single active child, optionally followed by one rest child; nested or
    conditional repeat structures are not silently flattened.
    """

    if isinstance(max_expanded_steps, bool) or not isinstance(max_expanded_steps, int):
        raise ValueError("max_expanded_steps must be a positive integer")
    if max_expanded_steps <= 0:
        raise ValueError("max_expanded_steps must be a positive integer")

    raw_steps = _top_level_steps(payload)
    expanded: list[dict[str, Any]] = []
    groups: list[RepeatGroupLayout] = []
    for index, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, Mapping):
            raise WorkoutStepDecodeError(
                f"workout step {index + 1} must be an object"
            )
        if _is_repeat_group(raw_step):
            group_steps, layout = _decode_repeat_group(
                raw_step,
                start_index=len(expanded),
                current_count=len(expanded),
                max_expanded_steps=max_expanded_steps,
            )
            expanded.extend(group_steps)
            groups.append(layout)
        else:
            _validate_executable_step(raw_step, f"workout step {index + 1}")
            if len(expanded) + 1 > max_expanded_steps:
                raise WorkoutStepDecodeError(
                    f"expanded workout step limit of {max_expanded_steps} exceeded"
                )
            expanded.append(deepcopy(dict(raw_step)))

    return DecodedWorkoutSteps(tuple(expanded), tuple(groups))


def _top_level_steps(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> list[Any]:
    if isinstance(payload, Mapping):
        segments = payload.get("workoutSegments")
        if isinstance(segments, list):
            result: list[Any] = []
            for index, segment in enumerate(segments):
                if not isinstance(segment, Mapping):
                    raise WorkoutStepDecodeError(
                        f"workoutSegments[{index}] must be an object"
                    )
                steps = segment.get("workoutSteps")
                if not isinstance(steps, list):
                    raise WorkoutStepDecodeError(
                        f"workoutSegments[{index}].workoutSteps must be an array"
                    )
                result.extend(steps)
            return result
        steps = payload.get("workoutSteps")
        if isinstance(steps, list):
            return list(steps)
        raise WorkoutStepDecodeError(
            "payload must contain workoutSegments[*].workoutSteps or workoutSteps"
        )
    if isinstance(payload, (str, bytes, bytearray)) or not isinstance(payload, Sequence):
        raise WorkoutStepDecodeError("workout steps must be an object or array")
    return list(payload)


def _decode_repeat_group(
    group: Mapping[str, Any],
    *,
    start_index: int,
    current_count: int,
    max_expanded_steps: int,
) -> tuple[list[dict[str, Any]], RepeatGroupLayout]:
    group_type = group.get("type")
    if group_type not in (None, "RepeatGroupDTO"):
        raise WorkoutStepDecodeError(
            f"unsupported repeat group type {group_type!r}"
        )
    iterations = group.get("numberOfIterations")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations <= 0:
        raise WorkoutStepDecodeError(
            "numberOfIterations must be a positive integer in RepeatGroupDTO"
        )
    skip_last_rest_step = group.get("skipLastRestStep", False)
    if not isinstance(skip_last_rest_step, bool):
        raise WorkoutStepDecodeError(
            "skipLastRestStep must be boolean in RepeatGroupDTO"
        )
    _validate_iteration_condition(group, iterations)

    raw_children = group.get("workoutSteps")
    if not isinstance(raw_children, list) or not raw_children:
        raise WorkoutStepDecodeError(
            "RepeatGroupDTO.workoutSteps must be a non-empty array"
        )
    if len(raw_children) > 2:
        raise WorkoutStepDecodeError(
            "unsupported repeat group shape: expected one active child and optional rest"
        )

    children: list[dict[str, Any]] = []
    for child_index, raw_child in enumerate(raw_children):
        if not isinstance(raw_child, Mapping):
            raise WorkoutStepDecodeError(
                f"RepeatGroupDTO.workoutSteps[{child_index}] must be an object"
            )
        if _is_repeat_group(raw_child) or "workoutSteps" in raw_child:
            raise WorkoutStepDecodeError(
                "nested repeat groups are not supported by the Garmin step decoder"
            )
        _validate_executable_step(
            raw_child, f"RepeatGroupDTO.workoutSteps[{child_index}]"
        )
        children.append(deepcopy(dict(raw_child)))

    if _is_rest_step(children[0]):
        raise WorkoutStepDecodeError(
            "RepeatGroupDTO must start with an active executable child"
        )
    if len(children) == 2 and not _is_rest_step(children[1]):
        raise WorkoutStepDecodeError(
            "RepeatGroupDTO second child must be a rest step"
        )

    expanded_count = len(children) * iterations
    if skip_last_rest_step and _is_rest_step(children[-1]):
        expanded_count -= 1
    if current_count + expanded_count > max_expanded_steps:
        raise WorkoutStepDecodeError(
            f"expanded workout step limit of {max_expanded_steps} exceeded"
        )

    expanded = [
        deepcopy(child)
        for iteration in range(iterations)
        for child_index, child in enumerate(children)
        if not (
            skip_last_rest_step
            and iteration == iterations - 1
            and child_index == len(children) - 1
            and _is_rest_step(child)
        )
    ]
    layout = RepeatGroupLayout(
        start_index=start_index,
        iterations=iterations,
        skip_last_rest_step=skip_last_rest_step,
        child_steps=tuple(children),
        child_step_id=group.get("childStepId"),
        step_order=group.get("stepOrder"),
        group_type=group.get("type"),
        step_type_key=(
            group.get("stepType", {}).get("stepTypeKey")
            if isinstance(group.get("stepType"), Mapping)
            else None
        ),
    )
    return expanded, layout


def _validate_iteration_condition(group: Mapping[str, Any], iterations: int) -> None:
    condition = group.get("endCondition")
    if condition is not None:
        if not isinstance(condition, Mapping):
            raise WorkoutStepDecodeError(
                "RepeatGroupDTO.endCondition must be an object"
            )
        condition_key = condition.get("conditionTypeKey")
        if condition_key not in (None, "iterations"):
            raise WorkoutStepDecodeError(
                "RepeatGroupDTO.endCondition must use iterations"
            )
    value = group.get("endConditionValue")
    if value is not None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise WorkoutStepDecodeError(
                "RepeatGroupDTO endConditionValue must match numberOfIterations"
            )
        if float(value) != float(iterations):
            raise WorkoutStepDecodeError(
                "RepeatGroupDTO endConditionValue must match numberOfIterations"
            )


def _validate_executable_step(step: Mapping[str, Any], path: str) -> None:
    if "workoutSteps" in step or _is_repeat_group(step):
        raise WorkoutStepDecodeError(f"unsupported repeat structure at {path}")
    step_type = step.get("type")
    if step_type not in (None, "ExecutableStepDTO"):
        raise WorkoutStepDecodeError(
            f"unsupported Garmin step type {step_type!r} at {path}"
        )
    step_type_data = step.get("stepType")
    if not isinstance(step_type_data, Mapping):
        raise WorkoutStepDecodeError(f"missing stepType at {path}")
    step_type_key = step_type_data.get("stepTypeKey")
    if not isinstance(step_type_key, str) or not step_type_key:
        raise WorkoutStepDecodeError(f"missing stepType.stepTypeKey at {path}")
    condition = step.get("endCondition")
    if not isinstance(condition, Mapping):
        raise WorkoutStepDecodeError(f"missing endCondition at {path}")
    condition_key = condition.get("conditionTypeKey")
    if not isinstance(condition_key, str) or not condition_key:
        raise WorkoutStepDecodeError(
            f"missing endCondition.conditionTypeKey at {path}"
        )


def _is_repeat_group(step: Mapping[str, Any]) -> bool:
    step_type = step.get("type")
    step_key = step.get("stepType", {})
    step_type_key = step_key.get("stepTypeKey") if isinstance(step_key, Mapping) else None
    return (
        step_type == "RepeatGroupDTO"
        or "RepeatGroup" in str(step_type)
        or step_type_key == "repeat"
        or "numberOfIterations" in step
    )


def _is_rest_step(step: Mapping[str, Any]) -> bool:
    step_type = step.get("stepType")
    return isinstance(step_type, Mapping) and step_type.get("stepTypeKey") == "rest"
