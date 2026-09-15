"""Safe inventory and template CRUD for Garmin planned workouts.

The functions in this module operate on exact remote IDs.  They read the full
remote resource before editing, preserve fields outside the supported semantic
surface, and require explicit authorization for every mutation.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, asdict
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from training_sync.config import planned_workout_journal_path
from training_sync.domain.planned_workout import PlannedWorkout
from training_sync.garmin.planned_workouts import (
    GarminWorkoutProjection,
    project_planned_workout,
)
from training_sync.use_cases.publish_workout import (
    _calendar_items,
    _account_key,
    _extract_schedule_id,
    _extract_workout_id,
    _Journal,
    _publication_lock,
    _workout_items,
    verify_saved_workout,
    publish_workout,
)
from training_sync.garmin.workout_steps import (
    DecodedWorkoutSteps,
    WorkoutStepDecodeError,
    decode_workout_steps,
)


class ManagementError(RuntimeError):
    """Base error for exact-resource management failures."""


class RemoteNotFoundError(ManagementError):
    """The requested exact remote resource does not exist."""


class RemotePermissionError(ManagementError):
    """Garmin denied access to the requested resource or operation."""


class UnsupportedRemoteStructureError(ManagementError):
    """The remote shape cannot be safely preserved by the requested edit."""


class StaleBaselineError(ManagementError):
    """The remote resource changed after the caller's baseline was captured."""


class CalendarOperationError(ManagementError):
    """A calendar occurrence could not be changed or verified safely."""


class ScheduleNotFoundError(CalendarOperationError):
    """An exact schedule ID is confirmed absent."""


@dataclass(frozen=True)
class WorkoutInventory:
    items: tuple[dict[str, Any], ...]
    incomplete: bool
    pages: int


@dataclass(frozen=True)
class ManagementResult:
    state: str
    workout_id: int | str | None = None
    schedule_id: int | str | None = None
    scope: str | None = None
    preview: str | None = None
    diff: dict[str, Any] | None = None
    preserved_fields: tuple[str, ...] = ()
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CalendarInventory:
    items: tuple[dict[str, Any], ...]
    incomplete: bool
    months: int


@dataclass(frozen=True)
class CalendarResult:
    state: str
    schedule_id: int | str | None = None
    workout_id: int | str | None = None
    original_schedule_id: int | str | None = None
    replacement_schedule_id: int | str | None = None
    replacement_workout_id: int | str | None = None
    date: str | None = None
    reused: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def list_workouts(
    client: Any,
    *,
    page_size: int = 100,
    max_pages: int = 10,
) -> WorkoutInventory:
    """List accessible workouts with an explicit bounded/incomplete result."""

    if page_size <= 0 or max_pages <= 0:
        raise ValueError("page_size and max_pages must be positive")
    method = getattr(client, "get_workouts", None)
    if method is None:
        raise ManagementError("Garmin client does not support workout inventory")

    items: list[dict[str, Any]] = []
    incomplete = False
    pages = 0
    for page in range(max_pages):
        pages += 1
        try:
            response = method(start=page * page_size, limit=page_size)
        except TypeError:
            try:
                response = method(page=page, limit=page_size)
            except TypeError:
                response = method()
                values, response_incomplete = _workout_items(response)
                items.extend(dict(value) for value in values)
                incomplete = response_incomplete or len(values) >= page_size
                break
        values, response_incomplete = _workout_items(response)
        items.extend(dict(value) for value in values)
        incomplete = incomplete or response_incomplete
        if len(values) < page_size:
            break
        if page == max_pages - 1:
            incomplete = True
    return WorkoutInventory(tuple(items), incomplete, pages)


def read_workout(client: Any, workout_id: int | str) -> dict[str, Any]:
    """Read one exact workout and translate common provider failures."""

    method = getattr(client, "get_workout_by_id", None)
    if method is None:
        method = getattr(client, "get_workout", None)
    if method is None:
        raise ManagementError("Garmin client does not support workout read-back")
    try:
        value = method(workout_id)
    except (KeyError, LookupError) as exc:
        raise RemoteNotFoundError(f"Garmin workout {workout_id} was not found") from exc
    except PermissionError as exc:
        raise RemotePermissionError(f"Garmin denied access to workout {workout_id}") from exc
    except Exception as exc:
        if _looks_like_permission_error(exc):
            raise RemotePermissionError(f"Garmin denied access to workout {workout_id}") from exc
        if _looks_like_not_found_error(exc):
            raise RemoteNotFoundError(f"Garmin workout {workout_id} was not found") from exc
        raise ManagementError(
            f"Garmin workout {workout_id} could not be read: {type(exc).__name__}"
        ) from exc
    if not isinstance(value, Mapping):
        raise ManagementError(f"Garmin workout {workout_id} read-back was not an object")
    return dict(value)


def update_workout(
    client: Any,
    workout_id: int | str,
    workout: PlannedWorkout,
    *,
    authorized: bool = False,
    yes: bool | None = None,
    baseline: Mapping[str, Any] | str | None = None,
    journal_path: Any | None = "__default__",
    account: str | None = None,
) -> ManagementResult:
    """Preview or update one shared template after an optimistic baseline check."""

    if yes is not None:
        authorized = yes
    current = read_workout(client, workout_id)
    projection = project_planned_workout(workout)
    desired = _merge_supported_update(current, projection)
    diff = _describe_diff(current, desired)
    if baseline is not None and _remote_hash(current) != _baseline_hash(baseline):
        raise StaleBaselineError(
            f"Garmin workout {workout_id} changed since preview; refresh the baseline"
        )
    if not authorized:
        return ManagementResult(
            state="preview",
            workout_id=workout_id,
            scope="template",
            preview=projection.preview,
            diff=diff,
            preserved_fields=tuple(_preserved_top_level_fields(current)),
        )
    path = _resolve_management_journal_path(journal_path)
    key = _calendar_journal_key(client, account, "update", str(workout_id))
    with _publication_lock(path, key):
        latest = read_workout(client, workout_id)
        if _remote_hash(latest) != _remote_hash(current):
            raise StaleBaselineError(
                f"Garmin workout {workout_id} changed before mutation; refresh the baseline"
            )
        current = latest
        desired = _merge_supported_update(current, projection)
        diff = _describe_diff(current, desired)
        _record_calendar_state(
            path,
            key,
            operation="update",
            state="updating",
            workout_id=workout_id,
        )
        try:
            _update_remote_workout(client, workout_id, desired)
            saved = read_workout(client, workout_id)
            verified, errors = verify_saved_workout(projection, saved)
            if not verified:
                raise ManagementError(
                    f"Garmin workout {workout_id} update verification failed: {'; '.join(errors)}"
                )
        except Exception as exc:
            _record_calendar_state(
                path,
                key,
                operation="update",
                state="uncertain",
                workout_id=workout_id,
                error=type(exc).__name__,
            )
            raise
        _record_calendar_state(
            path,
            key,
            operation="update",
            state="verified",
            workout_id=workout_id,
        )
        return ManagementResult(
            state="verified",
            workout_id=workout_id,
            scope="template",
            diff=diff,
            preserved_fields=tuple(_preserved_top_level_fields(current)),
        )


def duplicate_workout(
    client: Any,
    workout_id: int | str,
    *,
    name: str,
    authorized: bool = False,
    yes: bool | None = None,
    journal_path: Any | None = "__default__",
    account: str | None = None,
) -> ManagementResult:
    """Preview or duplicate an exact template without copying calendar entries."""

    if yes is not None:
        authorized = yes
    if not isinstance(name, str) or not name.strip():
        raise ValueError("duplicate name must be non-empty")
    original = read_workout(client, workout_id)
    _assert_editable_structure(original)
    desired = deepcopy(original)
    desired["workoutName"] = name.strip()
    desired.pop("workoutId", None)
    desired.pop("id", None)
    if not authorized:
        return ManagementResult(
            state="preview",
            workout_id=workout_id,
            scope="duplicate",
            diff={"workoutName": {"from": original.get("workoutName"), "to": name.strip()}},
        )
    path = _resolve_management_journal_path(journal_path)
    key = _calendar_journal_key(client, account, "duplicate", f"{workout_id}:{name.strip()}")
    with _publication_lock(path, key):
        _record_calendar_state(
            path,
            key,
            operation="duplicate",
            state="uploading",
            workout_id=workout_id,
        )
        try:
            response = _upload_remote_workout(client, desired)
            new_id = _extract_workout_id(response)
            if new_id is None:
                raise ManagementError("Garmin duplicate upload returned no workout ID")
            _record_calendar_state(
                path,
                key,
                operation="duplicate",
                state="uploaded",
                workout_id=new_id,
            )
            saved = read_workout(client, new_id)
            if not _duplicate_matches(desired, saved, name.strip()):
                raise ManagementError(
                    f"Garmin duplicate {new_id} failed read-back verification"
                )
        except Exception as exc:
            _record_calendar_state(
                path,
                key,
                operation="duplicate",
                state="uncertain",
                workout_id=locals().get("new_id"),
                error=type(exc).__name__,
            )
            raise
        _record_calendar_state(
            path,
            key,
            operation="duplicate",
            state="verified",
            workout_id=new_id,
        )
        return ManagementResult(
            state="verified",
            workout_id=new_id,
            scope="duplicate",
        )


def delete_workout(
    client: Any,
    workout_id: int | str,
    *,
    authorized: bool = False,
    yes: bool | None = None,
    journal_path: Any | None = "__default__",
    calendar_year: int | None = None,
    calendar_month: int | None = None,
    account: str | None = None,
) -> ManagementResult:
    """Preview or delete one exact, unreferenced template."""

    if yes is not None:
        authorized = yes
    existing = read_workout(client, workout_id)
    if not authorized:
        return ManagementResult(
            state="preview",
            workout_id=workout_id,
            scope="delete",
            diff={"impact": "calendar references must be checked before deletion"},
        )

    path = _resolve_management_journal_path(journal_path)
    key = _calendar_journal_key(client, account, "delete", str(workout_id))
    with _publication_lock(path, key):
        _record_calendar_state(
            path,
            key,
            operation="delete",
            state="checking_references",
            workout_id=workout_id,
        )
        references, complete = _calendar_references(
            client,
            workout_id,
            year=calendar_year,
            month=calendar_month,
        )
        if not complete:
            _record_calendar_state(
                path,
                key,
                operation="delete",
                state="blocked",
                workout_id=workout_id,
                error="incomplete scheduled reference inventory",
            )
            raise UnsupportedRemoteStructureError(
                "scheduled reference impact is incomplete; deletion is blocked"
            )
        if references:
            _record_calendar_state(
                path,
                key,
                operation="delete",
                state="blocked",
                workout_id=workout_id,
                error="scheduled references remain",
            )
            raise UnsupportedRemoteStructureError(
                f"scheduled references remain for workout {workout_id}; unschedule them first"
            )

        method = getattr(client, "delete_workout", None)
        if method is None:
            raise ManagementError("Garmin client does not support workout deletion")
        _record_calendar_state(
            path,
            key,
            operation="delete",
            state="deleting",
            workout_id=workout_id,
        )
        try:
            method(workout_id)
        except PermissionError as exc:
            raise RemotePermissionError(f"Garmin denied deletion of workout {workout_id}") from exc
        except Exception as exc:
            if _looks_like_permission_error(exc):
                raise RemotePermissionError(f"Garmin denied deletion of workout {workout_id}") from exc
            # The provider may have committed before the response failed.
            # Resolve that outcome read-only before allowing any retry.
            try:
                read_workout(client, workout_id)
            except RemoteNotFoundError:
                _record_calendar_state(
                    path,
                    key,
                    operation="delete",
                    state="verified",
                    workout_id=workout_id,
                )
                return ManagementResult(state="verified", workout_id=workout_id, scope="delete")
            except ManagementError as read_exc:
                _record_calendar_state(
                    path,
                    key,
                    operation="delete",
                    state="uncertain",
                    workout_id=workout_id,
                    error=type(read_exc).__name__,
                )
                raise ManagementError(
                    f"Garmin workout {workout_id} deletion outcome is uncertain"
                ) from read_exc
            raise ManagementError(f"Garmin workout deletion failed: {type(exc).__name__}") from exc
        try:
            read_workout(client, workout_id)
        except RemoteNotFoundError:
            _record_calendar_state(
                path,
                key,
                operation="delete",
                state="verified",
                workout_id=workout_id,
            )
            return ManagementResult(state="verified", workout_id=workout_id, scope="delete")
        except ManagementError as exc:
            _record_calendar_state(
                path,
                key,
                operation="delete",
                state="uncertain",
                workout_id=workout_id,
                error=type(exc).__name__,
            )
            raise ManagementError(
                f"Garmin workout {workout_id} deletion outcome is uncertain"
            ) from exc
        raise ManagementError(f"Garmin workout {workout_id} still exists after deletion")


def remote_payload_hash(payload: Mapping[str, Any]) -> str:
    """Return a stable hash for optimistic-concurrency baselines."""

    return _remote_hash(payload)


def _merge_supported_update(
    current: Mapping[str, Any],
    projection: GarminWorkoutProjection,
) -> dict[str, Any]:
    _assert_editable_structure(current)
    current_segments = current.get("workoutSegments")
    desired_segments = projection.payload.get("workoutSegments")
    if not isinstance(current_segments, list) or not isinstance(desired_segments, list):
        raise UnsupportedRemoteStructureError("workout segments are not editable")
    if len(current_segments) != len(desired_segments):
        raise UnsupportedRemoteStructureError(
            "changing the number of workout segments is unsafe for a template update"
        )

    result = deepcopy(dict(current))
    for key in (
        "workoutName",
        "sportType",
        "estimatedDurationInSecs",
        "description",
        "context",
    ):
        if key in projection.payload:
            result[key] = deepcopy(projection.payload[key])
    merged_segments: list[dict[str, Any]] = []
    for current_segment, desired_segment in zip(current_segments, desired_segments):
        if not isinstance(current_segment, Mapping) or not isinstance(desired_segment, Mapping):
            raise UnsupportedRemoteStructureError("workout segment is not an object")
        current_steps = current_segment.get("workoutSteps")
        desired_steps = desired_segment.get("workoutSteps")
        if not isinstance(current_steps, list) or not isinstance(desired_steps, list):
            raise UnsupportedRemoteStructureError("workout steps are not editable")
        current_decoded = _decode_segment_steps(current_steps, "current")
        desired_decoded = _decode_segment_steps(desired_steps, "desired")
        if len(current_decoded.steps) != len(desired_decoded.steps):
            raise UnsupportedRemoteStructureError(
                "changing the number of expanded executable steps is unsafe "
                "for a template update"
            )
        merged_segment = deepcopy(dict(current_segment))
        merged_steps = _merge_step_tree(
            current_steps,
            current_decoded,
            desired_steps,
            desired_decoded,
            segment_index=len(merged_segments),
        )
        merged_segment["workoutSteps"] = merged_steps
        merged_segments.append(merged_segment)
    result["workoutSegments"] = merged_segments
    return result


def _assert_editable_structure(payload: Mapping[str, Any]) -> DecodedWorkoutSteps:
    segments = payload.get("workoutSegments")
    if not isinstance(segments, list) or not segments:
        raise UnsupportedRemoteStructureError("workout has no editable segments")
    try:
        decoded = decode_workout_steps(payload)
    except WorkoutStepDecodeError as exc:
        raise UnsupportedRemoteStructureError(
            f"unsupported workout step structure: {exc}"
        ) from exc
    return decoded


def _decode_segment_steps(
    steps: list[Any],
    label: str,
) -> DecodedWorkoutSteps:
    try:
        return decode_workout_steps(steps)
    except WorkoutStepDecodeError as exc:
        raise UnsupportedRemoteStructureError(
            f"unsupported {label} workout step structure: {exc}"
        ) from exc


def _merge_step_tree(
    current_steps: list[Any],
    current_decoded: DecodedWorkoutSteps,
    desired_steps: list[Any],
    desired_decoded: DecodedWorkoutSteps,
    *,
    segment_index: int,
) -> list[dict[str, Any]]:
    """Merge desired semantics into a flat or grouped supported step tree."""

    current_physical = list(current_decoded.steps)
    desired_physical = list(desired_decoded.steps)
    current_group_payloads = _repeat_group_payloads(
        current_steps, current_decoded
    )
    desired_groups = {
        group.start_index: group for group in desired_decoded.repeat_groups
    }
    for start_index, current_group in current_group_payloads.items():
        if start_index not in desired_groups and _unrelated_group_metadata(current_group):
            raise UnsupportedRemoteStructureError(
                "group metadata cannot be preserved when changing the repeat layout"
            )
    merged: list[dict[str, Any]] = []
    current_index = 0
    desired_index = 0
    for desired_step in desired_steps:
        if not isinstance(desired_step, Mapping):
            raise UnsupportedRemoteStructureError(
                f"desired segment {segment_index + 1} contains a non-object step"
            )
        desired_group = desired_groups.get(desired_index)
        if desired_group is not None and _is_repeat_group_step(desired_step):
            child_count = len(desired_group.child_steps)
            if child_count == 0:
                raise UnsupportedRemoteStructureError(
                    "repeat group has no preservable child steps"
                )
            children: list[dict[str, Any]] = []
            for child_index, desired_child in enumerate(desired_group.child_steps):
                source_indexes = [
                    current_index + iteration * child_count + child_index
                    for iteration in range(desired_group.iterations)
                    if not (
                        desired_group.skip_last_rest_step
                        and iteration == desired_group.iterations - 1
                        and child_index == child_count - 1
                    )
                ]
                if not source_indexes or source_indexes[-1] >= len(current_physical):
                    raise UnsupportedRemoteStructureError(
                        "repeat group cannot be aligned with existing expanded execution"
                    )
                _ensure_metadata_consistent(
                    [current_physical[index] for index in source_indexes],
                    f"repeat group child {child_index + 1}",
                )
                children.append(
                    _merge_step(
                        current_physical[source_indexes[0]], desired_child
                    )
                )
            current_group = current_group_payloads.get(current_index)
            merged_group = _merge_group(
                current_group,
                desired_step,
                children,
            )
            merged.append(merged_group)
            current_index += desired_group.expanded_step_count
            desired_index += desired_group.expanded_step_count
            continue

        if current_index >= len(current_physical):
            raise UnsupportedRemoteStructureError(
                "desired step sequence cannot be aligned with existing execution"
            )
        merged.append(_merge_step(current_physical[current_index], desired_step))
        current_index += 1
        desired_index += 1

    if current_index != len(current_physical) or desired_index != len(desired_physical):
        raise UnsupportedRemoteStructureError(
            "step tree alignment did not consume the complete expanded execution"
        )
    return merged


def _merge_step(
    current_step: Mapping[str, Any],
    desired_step: Mapping[str, Any],
) -> dict[str, Any]:
    merged = deepcopy(dict(current_step))
    # Only semantic and hierarchy fields are replaced. Unknown provider
    # metadata attached to an aligned physical step remains untouched.
    for key in _editable_step_fields():
        if key in desired_step:
            merged[key] = deepcopy(desired_step[key])
    return merged


def _merge_group(
    current_group: Mapping[str, Any] | None,
    desired_group: Mapping[str, Any],
    children: list[dict[str, Any]],
) -> dict[str, Any]:
    merged = deepcopy(dict(current_group)) if current_group is not None else {}
    merged.update(deepcopy(dict(desired_group)))
    merged["workoutSteps"] = children
    return merged


def _repeat_group_payloads(
    steps: list[Any],
    decoded: DecodedWorkoutSteps,
) -> dict[int, Mapping[str, Any]]:
    """Index raw top-level groups by their expanded start position."""

    layouts = {group.start_index: group for group in decoded.repeat_groups}
    result: dict[int, Mapping[str, Any]] = {}
    expanded_index = 0
    for step in steps:
        if isinstance(step, Mapping) and _is_repeat_group_step(step):
            layout = layouts.get(expanded_index)
            if layout is not None:
                result[expanded_index] = step
                expanded_index += layout.expanded_step_count
                continue
        expanded_index += 1
    return result


def _ensure_metadata_consistent(
    steps: list[Mapping[str, Any]],
    label: str,
) -> None:
    if len(steps) < 2:
        return
    baseline = _unrelated_step_metadata(steps[0])
    for step in steps[1:]:
        if _unrelated_step_metadata(step) != baseline:
            raise UnsupportedRemoteStructureError(
                f"conflicting provider metadata in {label}; "
                "one grouped child cannot preserve per-set metadata"
            )


def _unrelated_step_metadata(step: Mapping[str, Any]) -> dict[str, Any]:
    excluded = set(_editable_step_fields()) | {
        "workoutSteps",
        "id",
        "numberOfIterations",
        "skipLastRestStep",
        "stepId",
        "stepID",
        "workoutStepId",
        "workoutStepID",
        "step_id",
        "parentStepId",
    }
    return {
        key: deepcopy(value)
        for key, value in step.items()
        if key not in excluded
    }


def _unrelated_group_metadata(group: Mapping[str, Any]) -> dict[str, Any]:
    known = {
        "type",
        "stepOrder",
        "childStepId",
        "description",
        "stepType",
        "endCondition",
        "endConditionValue",
        "numberOfIterations",
        "skipLastRestStep",
        "workoutSteps",
        "id",
        "groupId",
        "groupID",
        "repeatGroupId",
        "repeatGroupID",
    }
    return {
        key: deepcopy(value)
        for key, value in group.items()
        if key not in known
    }


def _is_repeat_group_step(step: Mapping[str, Any]) -> bool:
    return (
        step.get("type") == "RepeatGroupDTO"
        or "RepeatGroup" in str(step.get("type") or "")
        or (isinstance(step.get("stepType"), Mapping) and step["stepType"].get("stepTypeKey") == "repeat")
        or "numberOfIterations" in step
    )


def _editable_step_fields() -> tuple[str, ...]:
    return (
        "type",
        "stepOrder",
        "childStepId",
        "description",
        "stepType",
        "endCondition",
        "endConditionValue",
        "preferredEndConditionUnit",
        "endConditionCompare",
        "targetType",
        "targetValueOne",
        "targetValueTwo",
        "targetValueUnit",
        "category",
        "exerciseName",
        "originalExerciseName",
        "garminName",
        "repetitionCount",
        "weightValue",
        "weightUnit",
        "weightBasis",
        "loadKind",
        "side",
    )


def _describe_diff(current: Mapping[str, Any], desired: Mapping[str, Any]) -> dict[str, Any]:
    changed = [
        key
        for key in ("workoutName", "sportType", "estimatedDurationInSecs", "description")
        if current.get(key) != desired.get(key)
    ]
    current_steps = _steps(current)
    desired_steps = _steps(desired)
    for index, (old, new) in enumerate(zip(current_steps, desired_steps), start=1):
        for key in ("endCondition", "endConditionValue", "targetType", "targetValueOne", "targetValueTwo", "targetValueUnit", "weightValue", "weightUnit", "weightBasis", "side", "repetitionCount"):
            if old.get(key) != new.get(key):
                changed.append(f"step[{index}].{key}")
    return {"changed": changed, "scope": "template"}


def _preserved_top_level_fields(payload: Mapping[str, Any]) -> list[str]:
    return [
        key
        for key in payload
        if key not in {"workoutName", "sportType", "estimatedDurationInSecs", "description", "workoutSegments"}
    ]


def _steps(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    try:
        return list(decode_workout_steps(payload).steps)
    except WorkoutStepDecodeError as exc:
        raise UnsupportedRemoteStructureError(
            f"unsupported workout step structure: {exc}"
        ) from exc


def _remote_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _baseline_hash(value: Mapping[str, Any] | str) -> str:
    return value if isinstance(value, str) else _remote_hash(value)


def _update_remote_workout(client: Any, workout_id: int | str, payload: Mapping[str, Any]) -> Any:
    method = getattr(client, "update_workout", None)
    if method is None:
        method = getattr(client, "put_workout", None)
    if method is None:
        # garminconnect 0.3.x exposes upload/delete but not a typed update
        # wrapper. Keep the endpoint isolated here instead of scattering raw
        # HTTP calls through the use case; callers without this transport get
        # an actionable refusal rather than a lossy re-upload.
        transport = getattr(client, "client", None)
        base_path = getattr(client, "garmin_workouts", None)
        put = getattr(transport, "put", None)
        if callable(put) and isinstance(base_path, str):
            url = f"{base_path}/workout/{workout_id}"
            try:
                return put("connectapi", url, json=dict(payload), api=True)
            except PermissionError as exc:
                raise RemotePermissionError(
                    f"Garmin denied update of workout {workout_id}"
                ) from exc
            except Exception as exc:
                if _looks_like_permission_error(exc):
                    raise RemotePermissionError(
                        f"Garmin denied update of workout {workout_id}"
                    ) from exc
                raise ManagementError(
                    f"Garmin workout update failed: {type(exc).__name__}"
                ) from exc
        raise ManagementError(
            "installed Garmin client has no safe workout update method; "
            "inspect/update through a compatible adapter first"
        )
    try:
        return method(workout_id, dict(payload))
    except PermissionError as exc:
        raise RemotePermissionError(f"Garmin denied update of workout {workout_id}") from exc
    except Exception as exc:
        if _looks_like_permission_error(exc):
            raise RemotePermissionError(f"Garmin denied update of workout {workout_id}") from exc
        raise ManagementError(f"Garmin workout update failed: {type(exc).__name__}") from exc


def _upload_remote_workout(client: Any, payload: Mapping[str, Any]) -> Any:
    method = getattr(client, "upload_workout", None)
    if method is None:
        method = getattr(client, "create_workout", None)
    if method is None:
        raise ManagementError("Garmin client does not support workout upload")
    return method(dict(payload))


def _duplicate_matches(
    expected: Mapping[str, Any],
    saved: Mapping[str, Any],
    expected_name: str,
) -> bool:
    if saved.get("workoutName") != expected_name:
        return False
    try:
        expected_decoded = decode_workout_steps(expected)
        saved_decoded = decode_workout_steps(saved)
    except WorkoutStepDecodeError:
        return False
    if [
        _semantic_step_key(step) for step in expected_decoded.steps
    ] != [
        _semantic_step_key(step) for step in saved_decoded.steps
    ]:
        return False
    expected_layout = [
        (
            group.start_index,
            group.iterations,
            group.skip_last_rest_step,
            len(group.child_steps),
            group.group_type,
            group.step_type_key,
        )
        for group in expected_decoded.repeat_groups
    ]
    saved_layout = [
        (
            group.start_index,
            group.iterations,
            group.skip_last_rest_step,
            len(group.child_steps),
            group.group_type,
            group.step_type_key,
        )
        for group in saved_decoded.repeat_groups
    ]
    return expected_layout == saved_layout


def _semantic_step_key(step: Mapping[str, Any]) -> str:
    """Ignore provider-assigned ordering and child IDs during duplicate checks."""

    return json.dumps(
        {
            key: value
            for key, value in step.items()
            if key not in {
                "stepOrder",
                "childStepId",
                "id",
                "stepId",
                "stepID",
                "workoutStepId",
                "workoutStepID",
                "step_id",
                "parentStepId",
            }
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _calendar_references(
    client: Any,
    workout_id: int | str,
    *,
    year: int | None,
    month: int | None,
) -> tuple[list[Mapping[str, Any]], bool]:
    method = getattr(client, "get_scheduled_workouts", None)
    if method is None:
        return [], False
    chosen = date.today()
    year = chosen.year if year is None else year
    month = chosen.month if month is None else month
    try:
        response = method(year, month)
    except PermissionError as exc:
        raise RemotePermissionError("Garmin denied calendar reference lookup") from exc
    except Exception as exc:
        if _looks_like_permission_error(exc):
            raise RemotePermissionError("Garmin denied calendar reference lookup") from exc
        raise UnsupportedRemoteStructureError(
            f"calendar reference lookup failed: {type(exc).__name__}"
        ) from exc
    references = [
        item
        for item in _calendar_items(response)
        if _schedule_workout_id(item) is not None
        and str(_schedule_workout_id(item)) == str(workout_id)
    ]
    if isinstance(response, Mapping) and response.get("incomplete"):
        return references, False
    # The Garmin endpoint is monthly. Callers can choose a month explicitly;
    # a response that does not advertise incompleteness is complete for that
    # bounded query, which is enough for exact tests and avoids guessing IDs.
    return references, True


def _schedule_workout_id(item: Mapping[str, Any]) -> int | str | None:
    for key in ("workoutId", "workoutID", "workout_id"):
        value = item.get(key)
        if isinstance(value, (int, str)) and not isinstance(value, bool):
            return value
    for key in ("workout", "workoutSummary"):
        value = _extract_workout_id(item.get(key))
        if value is not None:
            return value
    return None


def _looks_like_permission_error(error: Exception) -> bool:
    text = str(error).lower()
    return any(value in text for value in ("forbidden", "permission", "unauthorized", "403"))


def _looks_like_not_found_error(error: Exception) -> bool:
    text = str(error).lower()
    return "404" in text or "not found" in text or "does not exist" in text


def list_calendar(
    client: Any,
    from_date: str,
    to_date: str,
) -> CalendarInventory:
    """List exact calendar entries in the inclusive local-date range."""

    start = _calendar_date(from_date)
    end = _calendar_date(to_date)
    if start > end:
        raise ValueError("from_date must not be after to_date")
    method = getattr(client, "get_scheduled_workouts", None)
    if method is None:
        raise CalendarOperationError("Garmin client does not support calendar inventory")

    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    months = 0
    incomplete = False
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        months += 1
        try:
            response = method(cursor.year, cursor.month)
        except PermissionError as exc:
            raise RemotePermissionError("Garmin denied calendar inventory") from exc
        except Exception as exc:
            if _looks_like_permission_error(exc):
                raise RemotePermissionError("Garmin denied calendar inventory") from exc
            raise CalendarOperationError(
                f"calendar inventory failed: {type(exc).__name__}"
            ) from exc
        if isinstance(response, Mapping) and response.get("incomplete"):
            incomplete = True
        for item in _calendar_items(response):
            item_date = _item_calendar_date(item)
            item_id = _extract_schedule_id(item)
            if item_date is None or not (start.isoformat() <= item_date <= end.isoformat()):
                continue
            unique_key = str(item_id) if item_id is not None else json.dumps(item, sort_keys=True)
            if unique_key in seen_ids:
                continue
            seen_ids.add(unique_key)
            entries.append(dict(item))
        cursor = _next_month(cursor)
    return CalendarInventory(tuple(entries), incomplete, months)


def schedule_calendar_workout(
    client: Any,
    workout_id: int | str,
    schedule_date: str,
    *,
    authorized: bool = False,
    yes: bool | None = None,
    journal_path: Any | None = "__default__",
    account: str | None = None,
) -> CalendarResult:
    """Schedule one exact template/date, reusing an existing exact occurrence."""

    if yes is not None:
        authorized = yes
    requested = _calendar_date(schedule_date).isoformat()
    read_workout(client, workout_id)
    if not authorized:
        return CalendarResult(
            state="preview",
            workout_id=workout_id,
            date=requested,
        )
    path = _resolve_management_journal_path(journal_path)
    key = _calendar_journal_key(client, account, "schedule", f"{workout_id}:{requested}")
    with _publication_lock(path, key):
        return _schedule_calendar_authorized(
            client,
            workout_id,
            requested,
            path=path,
            key=key,
        )


def _schedule_calendar_authorized(
    client: Any,
    workout_id: int | str,
    requested: str,
    *,
    path: Any,
    key: str,
) -> CalendarResult:
    existing = _calendar_matches(client, workout_id, requested)
    if len(existing) > 1:
        raise CalendarOperationError(
            f"multiple exact calendar occurrences already exist for workout {workout_id} on {requested}"
        )
    if existing:
        schedule_id = _extract_schedule_id(existing[0])
        if schedule_id is not None and _verify_calendar_entry(
            client, schedule_id, workout_id, requested
        )[0]:
            _record_calendar_state(
                path,
                key,
                operation="schedule",
                state="scheduled",
                workout_id=workout_id,
                schedule_id=schedule_id,
                schedule_date=requested,
            )
            return CalendarResult(
                state="verified",
                schedule_id=schedule_id,
                workout_id=workout_id,
                date=requested,
                reused=True,
            )

    method = getattr(client, "schedule_workout", None)
    if method is None:
        raise CalendarOperationError("Garmin client does not support calendar scheduling")
    _record_calendar_state(
        path,
        key,
        operation="schedule",
        state="scheduling",
        workout_id=workout_id,
        schedule_date=requested,
    )
    try:
        response = method(workout_id, requested)
        schedule_id = _extract_schedule_id(response)
        if schedule_id is None:
            schedule_id = _find_schedule_id(client, workout_id, requested)
        if schedule_id is None:
            raise CalendarOperationError("Garmin returned no schedule ID")
    except Exception as exc:
        try:
            matches = _calendar_matches(client, workout_id, requested)
        except Exception as reconcile_exc:
            _record_calendar_state(
                path,
                key,
                operation="schedule",
                state="uncertain",
                workout_id=workout_id,
                schedule_date=requested,
                error=type(reconcile_exc).__name__,
            )
            return CalendarResult(
                state="uncertain",
                workout_id=workout_id,
                date=requested,
                error=(
                    "calendar scheduling outcome uncertain; reconciliation failed: "
                    f"{type(reconcile_exc).__name__}"
                ),
            )
        if len(matches) == 1:
            schedule_id = _extract_schedule_id(matches[0])
            if schedule_id is not None and _verify_calendar_entry(
                client, schedule_id, workout_id, requested
            )[0]:
                _record_calendar_state(
                    path,
                    key,
                    operation="schedule",
                    state="scheduled",
                    workout_id=workout_id,
                    schedule_id=schedule_id,
                    schedule_date=requested,
                )
                return CalendarResult(
                    state="verified",
                    schedule_id=schedule_id,
                    workout_id=workout_id,
                    date=requested,
                    reused=True,
                )
        _record_calendar_state(
            path,
            key,
            operation="schedule",
            state="uncertain",
            workout_id=workout_id,
            schedule_date=requested,
            error=f"{type(exc).__name__}",
        )
        return CalendarResult(
            state="uncertain",
            workout_id=workout_id,
            date=requested,
            error=f"calendar scheduling outcome uncertain: {type(exc).__name__}",
        )
    verified, errors = _verify_calendar_entry(client, schedule_id, workout_id, requested)
    if not verified:
        _record_calendar_state(
            path,
            key,
            operation="schedule",
            state="verification_failed",
            workout_id=workout_id,
            schedule_id=schedule_id,
            schedule_date=requested,
            error="; ".join(errors),
        )
        return CalendarResult(
            state="verification_failed",
            schedule_id=schedule_id,
            workout_id=workout_id,
            date=requested,
            error="; ".join(errors),
        )
    _record_calendar_state(
        path,
        key,
        operation="schedule",
        state="scheduled",
        workout_id=workout_id,
        schedule_id=schedule_id,
        schedule_date=requested,
    )
    return CalendarResult(
        state="verified",
        schedule_id=schedule_id,
        workout_id=workout_id,
        date=requested,
    )


def move_calendar_workout(
    client: Any,
    schedule_id: int | str,
    new_date: str,
    *,
    authorized: bool = False,
    yes: bool | None = None,
    journal_path: Any | None = "__default__",
    account: str | None = None,
) -> CalendarResult:
    """Move one occurrence by verified add-then-remove ordering."""

    if yes is not None:
        authorized = yes
    destination = _calendar_date(new_date).isoformat()
    original = _read_calendar_entry(client, schedule_id)
    workout_id = _schedule_workout_id(original)
    if workout_id is None:
        raise CalendarOperationError(f"schedule {schedule_id} has no exact workout ID")
    if not authorized:
        return CalendarResult(
            state="preview",
            workout_id=workout_id,
            original_schedule_id=schedule_id,
            date=destination,
        )
    path = _resolve_management_journal_path(journal_path)
    key = _calendar_journal_key(client, account, "move", str(schedule_id))
    _record_calendar_state(
        path,
        key,
        operation="move",
        state="adding_replacement",
        workout_id=workout_id,
        schedule_id=schedule_id,
        schedule_date=destination,
    )
    existing = _calendar_matches(client, workout_id, destination)
    if len(existing) > 1:
        raise CalendarOperationError("destination calendar occurrence is ambiguous")
    replacement_id: int | str | None = None
    if existing:
        replacement_id = _extract_schedule_id(existing[0])
        if replacement_id is None or not _verify_calendar_entry(
            client, replacement_id, workout_id, destination
        )[0]:
            raise CalendarOperationError("destination occurrence could not be verified")
    else:
        method = getattr(client, "schedule_workout", None)
        if method is None:
            raise CalendarOperationError("Garmin client does not support calendar scheduling")
        try:
            response = method(workout_id, destination)
            replacement_id = _extract_schedule_id(response)
            if replacement_id is None:
                replacement_id = _find_schedule_id(client, workout_id, destination)
            if replacement_id is None:
                raise CalendarOperationError("Garmin returned no replacement schedule ID")
        except Exception as exc:
            _record_calendar_state(
                path,
                key,
                operation="move",
                state="uncertain",
                workout_id=workout_id,
                schedule_id=schedule_id,
                schedule_date=destination,
                error=type(exc).__name__,
            )
            return CalendarResult(
                state="uncertain",
                workout_id=workout_id,
                original_schedule_id=schedule_id,
                date=destination,
                error=f"move scheduling outcome uncertain: {type(exc).__name__}",
            )
        verified, errors = _verify_calendar_entry(
            client, replacement_id, workout_id, destination
        )
        if not verified:
            _record_calendar_state(
                path,
                key,
                operation="move",
                state="partial",
                workout_id=workout_id,
                schedule_id=schedule_id,
                schedule_date=destination,
                error="replacement read-back failed",
            )
            return CalendarResult(
                state="partial",
                workout_id=workout_id,
                original_schedule_id=schedule_id,
                replacement_schedule_id=replacement_id,
                date=destination,
                error="; ".join(errors),
            )
    _record_calendar_state(
        path,
        key,
        operation="move",
        state="removing_original",
        workout_id=workout_id,
        schedule_id=schedule_id,
        schedule_date=destination,
    )
    try:
        with _publication_lock(path, key):
            _unschedule(client, schedule_id)
    except Exception as exc:
        _record_calendar_state(
            path,
            key,
            operation="move",
            state="partial",
            workout_id=workout_id,
            schedule_id=schedule_id,
            schedule_date=destination,
            error=type(exc).__name__,
        )
        return CalendarResult(
            state="partial",
            workout_id=workout_id,
            original_schedule_id=schedule_id,
            replacement_schedule_id=replacement_id,
            date=destination,
            error=f"replacement verified but original removal failed: {type(exc).__name__}",
        )
    original_exists = _calendar_exists(client, schedule_id)
    if original_exists is None:
        _record_calendar_state(
            path,
            key,
            operation="move",
            state="uncertain",
            workout_id=workout_id,
            schedule_id=schedule_id,
            schedule_date=destination,
            error="original absence read-back unavailable",
        )
        return CalendarResult(
            state="uncertain",
            workout_id=workout_id,
            original_schedule_id=schedule_id,
            replacement_schedule_id=replacement_id,
            date=destination,
            error="replacement exists but original absence could not be read back",
        )
    if original_exists:
        _record_calendar_state(
            path,
            key,
            operation="move",
            state="partial",
            workout_id=workout_id,
            schedule_id=schedule_id,
            schedule_date=destination,
            error="original occurrence remains",
        )
        return CalendarResult(
            state="partial",
            workout_id=workout_id,
            original_schedule_id=schedule_id,
            replacement_schedule_id=replacement_id,
            date=destination,
            error="replacement exists but original occurrence remains",
        )
    _record_calendar_state(
        path,
        key,
        operation="move",
        state="verified",
        workout_id=workout_id,
        schedule_id=schedule_id,
        schedule_date=destination,
    )
    return CalendarResult(
        state="verified",
        workout_id=workout_id,
        original_schedule_id=schedule_id,
        replacement_schedule_id=replacement_id,
        date=destination,
    )


def remove_calendar_workout(
    client: Any,
    schedule_id: int | str,
    *,
    authorized: bool = False,
    yes: bool | None = None,
    journal_path: Any | None = "__default__",
    account: str | None = None,
) -> CalendarResult:
    """Remove one exact occurrence while leaving its template intact."""

    if yes is not None:
        authorized = yes
    path = _resolve_management_journal_path(journal_path)
    key = _calendar_journal_key(client, account, "remove", str(schedule_id))
    try:
        existing = _read_calendar_entry(client, schedule_id)
    except ScheduleNotFoundError:
        entry = _Journal(path).get(key) if path is not None else None
        if entry is not None and entry.get("state") in {"unscheduling", "uncertain"}:
            _record_calendar_state(
                path,
                key,
                operation="remove",
                state="verified",
                workout_id=entry.get("workout_id"),
                schedule_id=schedule_id,
                schedule_date=entry.get("schedule_date"),
            )
            return CalendarResult(
                state="verified",
                schedule_id=schedule_id,
                workout_id=entry.get("workout_id"),
                original_schedule_id=schedule_id,
                date=entry.get("schedule_date"),
            )
        raise
    workout_id = _schedule_workout_id(existing)
    item_date = _item_calendar_date(existing)
    if not authorized:
        return CalendarResult(
            state="preview",
            schedule_id=schedule_id,
            workout_id=workout_id,
            original_schedule_id=schedule_id,
            date=item_date,
        )
    with _publication_lock(path, key):
        _record_calendar_state(
            path,
            key,
            operation="remove",
            state="unscheduling",
            workout_id=workout_id,
            schedule_id=schedule_id,
            schedule_date=item_date,
        )
        try:
            _unschedule(client, schedule_id)
        except Exception as exc:
            _record_calendar_state(
                path,
                key,
                operation="remove",
                state="uncertain",
                workout_id=workout_id,
                schedule_id=schedule_id,
                schedule_date=item_date,
                error=type(exc).__name__,
            )
            return CalendarResult(
                state="uncertain",
                schedule_id=schedule_id,
                workout_id=workout_id,
                original_schedule_id=schedule_id,
                date=item_date,
                error=f"calendar removal outcome uncertain: {type(exc).__name__}",
            )
    original_exists = _calendar_exists(client, schedule_id)
    if original_exists is None:
        _record_calendar_state(
            path,
            key,
            operation="remove",
            state="uncertain",
            workout_id=workout_id,
            schedule_id=schedule_id,
            schedule_date=item_date,
            error="absence read-back unavailable",
        )
        return CalendarResult(
            state="uncertain",
            schedule_id=schedule_id,
            workout_id=workout_id,
            original_schedule_id=schedule_id,
            date=item_date,
            error="calendar removal succeeded but absence read-back is unavailable",
        )
    if original_exists:
        _record_calendar_state(
            path,
            key,
            operation="remove",
            state="verification_failed",
            workout_id=workout_id,
            schedule_id=schedule_id,
            schedule_date=item_date,
            error="occurrence still exists",
        )
        return CalendarResult(
            state="verification_failed",
            schedule_id=schedule_id,
            workout_id=workout_id,
            original_schedule_id=schedule_id,
            date=item_date,
            error="calendar occurrence still exists after removal",
        )
    _record_calendar_state(
        path,
        key,
        operation="remove",
        state="verified",
        workout_id=workout_id,
        schedule_id=schedule_id,
        schedule_date=item_date,
    )
    return CalendarResult(
        state="verified",
        schedule_id=schedule_id,
        workout_id=workout_id,
        original_schedule_id=schedule_id,
        date=item_date,
    )


def replace_calendar_workout(
    client: Any,
    schedule_id: int | str,
    workout: PlannedWorkout,
    *,
    authorized: bool = False,
    yes: bool | None = None,
    journal_path: Any | None = "__default__",
    account: str | None = None,
) -> CalendarResult:
    """Create/verify/schedule a date-specific variant before removing old entry."""

    if yes is not None:
        authorized = yes
    original = _read_calendar_entry(client, schedule_id)
    old_workout_id = _schedule_workout_id(original)
    old_date = _item_calendar_date(original)
    if old_workout_id is None or old_date is None:
        raise CalendarOperationError("selected schedule has incomplete identity")
    projection = project_planned_workout(workout)
    if not authorized:
        return CalendarResult(
            state="preview",
            workout_id=old_workout_id,
            original_schedule_id=schedule_id,
            date=old_date,
        )
    path = _resolve_management_journal_path(journal_path)
    key = _calendar_journal_key(client, account, "replace", str(schedule_id))
    _record_calendar_state(
        path,
        key,
        operation="replace",
        state="creating_variant",
        workout_id=old_workout_id,
        schedule_id=schedule_id,
        schedule_date=old_date,
    )
    published = publish_workout(
        client,
        workout,
        authorized=True,
        schedule_date=old_date,
        journal_path=journal_path,
    )
    if published.state not in {"scheduled"} or published.workout_id is None:
        _record_calendar_state(
            path,
            key,
            operation="replace",
            state="uncertain" if published.state == "uncertain" else "partial",
            workout_id=old_workout_id,
            schedule_id=schedule_id,
            schedule_date=old_date,
            error=published.error,
        )
        return CalendarResult(
            state="uncertain" if published.state == "uncertain" else "partial",
            workout_id=old_workout_id,
            original_schedule_id=schedule_id,
            replacement_workout_id=published.workout_id,
            replacement_schedule_id=published.schedule_id,
            date=old_date,
            error=published.error,
        )
    _record_calendar_state(
        path,
        key,
        operation="replace",
        state="removing_original",
        workout_id=old_workout_id,
        schedule_id=schedule_id,
        schedule_date=old_date,
    )
    try:
        with _publication_lock(path, key):
            _unschedule(client, schedule_id)
    except Exception as exc:
        _record_calendar_state(
            path,
            key,
            operation="replace",
            state="partial",
            workout_id=old_workout_id,
            schedule_id=schedule_id,
            schedule_date=old_date,
            error=type(exc).__name__,
        )
        return CalendarResult(
            state="partial",
            workout_id=old_workout_id,
            original_schedule_id=schedule_id,
            replacement_workout_id=published.workout_id,
            replacement_schedule_id=published.schedule_id,
            date=old_date,
            error=f"replacement verified but original removal failed: {type(exc).__name__}",
        )
    original_exists = _calendar_exists(client, schedule_id)
    if original_exists is None:
        _record_calendar_state(
            path,
            key,
            operation="replace",
            state="uncertain",
            workout_id=old_workout_id,
            schedule_id=schedule_id,
            schedule_date=old_date,
            error="original absence read-back unavailable",
        )
        return CalendarResult(
            state="uncertain",
            workout_id=old_workout_id,
            original_schedule_id=schedule_id,
            replacement_workout_id=published.workout_id,
            replacement_schedule_id=published.schedule_id,
            date=old_date,
            error="replacement exists but original absence could not be read back",
        )
    if original_exists:
        _record_calendar_state(
            path,
            key,
            operation="replace",
            state="partial",
            workout_id=old_workout_id,
            schedule_id=schedule_id,
            schedule_date=old_date,
            error="original occurrence remains",
        )
        return CalendarResult(
            state="partial",
            workout_id=old_workout_id,
            original_schedule_id=schedule_id,
            replacement_workout_id=published.workout_id,
            replacement_schedule_id=published.schedule_id,
            date=old_date,
            error="replacement exists but original occurrence remains",
        )
    _record_calendar_state(
        path,
        key,
        operation="replace",
        state="verified",
        workout_id=old_workout_id,
        schedule_id=schedule_id,
        schedule_date=old_date,
    )
    return CalendarResult(
        state="verified",
        workout_id=old_workout_id,
        original_schedule_id=schedule_id,
        replacement_workout_id=published.workout_id,
        replacement_schedule_id=published.schedule_id,
        date=old_date,
    )


# Command-oriented aliases keep the use case discoverable for the CLI and
# callers that prefer an explicit calendar namespace.
calendar_list = list_calendar
calendar_schedule = schedule_calendar_workout
calendar_move = move_calendar_workout
calendar_remove = remove_calendar_workout
calendar_replace = replace_calendar_workout
get_workouts = list_workouts
show_workout = read_workout
update_planned_workout = update_workout
duplicate_planned_workout = duplicate_workout
delete_planned_workout = delete_workout


def _calendar_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("calendar dates must be ISO dates")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("calendar dates must be ISO dates") from exc


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _read_calendar_entry(client: Any, schedule_id: int | str) -> dict[str, Any]:
    method = getattr(client, "get_scheduled_workout_by_id", None)
    if method is None:
        raise CalendarOperationError("Garmin client does not support exact schedule read-back")
    try:
        value = method(schedule_id)
    except (KeyError, LookupError) as exc:
        raise ScheduleNotFoundError(f"schedule {schedule_id} was not found") from exc
    except PermissionError as exc:
        raise RemotePermissionError(f"Garmin denied schedule {schedule_id}") from exc
    except Exception as exc:
        if _looks_like_permission_error(exc):
            raise RemotePermissionError(f"Garmin denied schedule {schedule_id}") from exc
        if _looks_like_not_found_error(exc):
            raise ScheduleNotFoundError(f"schedule {schedule_id} was not found") from exc
        raise CalendarOperationError(
            f"schedule {schedule_id} could not be read: {type(exc).__name__}"
        ) from exc
    if not isinstance(value, Mapping):
        raise CalendarOperationError(f"schedule {schedule_id} read-back was not an object")
    return dict(value)


def _calendar_matches(
    client: Any,
    workout_id: int | str,
    schedule_date: str,
) -> list[Mapping[str, Any]]:
    inventory = list_calendar(client, schedule_date, schedule_date)
    if inventory.incomplete:
        raise CalendarOperationError(
            f"calendar inventory is incomplete for {schedule_date}; exact retry is unsafe"
        )
    return [
        item
        for item in inventory.items
        if _schedule_workout_id(item) is not None
        and str(_schedule_workout_id(item)) == str(workout_id)
        and _item_calendar_date(item) == schedule_date
    ]


def _verify_calendar_entry(
    client: Any,
    schedule_id: int | str,
    workout_id: int | str,
    schedule_date: str,
) -> tuple[bool, tuple[str, ...]]:
    try:
        saved = _read_calendar_entry(client, schedule_id)
    except ManagementError as exc:
        return False, (str(exc),)
    errors: list[str] = []
    if _item_calendar_date(saved) != schedule_date:
        errors.append("calendar date mismatch")
    if _schedule_workout_id(saved) is None or str(_schedule_workout_id(saved)) != str(workout_id):
        errors.append("calendar workout ID mismatch")
    return not errors, tuple(errors)


def _find_schedule_id(client: Any, workout_id: int | str, schedule_date: str) -> int | str | None:
    matches = _calendar_matches(client, workout_id, schedule_date)
    if len(matches) == 1:
        return _extract_schedule_id(matches[0])
    return None


def _unschedule(client: Any, schedule_id: int | str) -> Any:
    method = getattr(client, "unschedule_workout", None)
    if method is None:
        raise CalendarOperationError("Garmin client does not support occurrence removal")
    return method(schedule_id)


def _calendar_exists(client: Any, schedule_id: int | str) -> bool | None:
    try:
        _read_calendar_entry(client, schedule_id)
    except ScheduleNotFoundError:
        return False
    except CalendarOperationError:
        return None
    return True


def _item_calendar_date(value: Mapping[str, Any]) -> str | None:
    for key in ("date", "scheduledDate", "calendarDate", "scheduleDate"):
        raw = value.get(key)
        if isinstance(raw, str):
            return raw[:10]
    return None


def _resolve_management_journal_path(value: Any) -> Any:
    if value == "__default__":
        return planned_workout_journal_path()
    return None if value is None else Path(value).expanduser()


def _calendar_journal_key(
    client: Any,
    account: str | None,
    operation: str,
    resource: str,
) -> str:
    return f"{_account_key(client, account)}\0calendar:{operation}:{resource}"


def _record_calendar_state(
    path: Any,
    key: str,
    *,
    operation: str,
    state: str,
    workout_id: int | str | None = None,
    schedule_id: int | str | None = None,
    schedule_date: str | None = None,
    error: str | None = None,
) -> None:
    if path is None:
        return
    journal = _Journal(path)
    entry = journal.get(key) or {}
    entry.update({"account_resource": key, "operation": operation, "state": state})
    if workout_id is not None:
        entry["workout_id"] = workout_id
    if schedule_id is not None:
        entry["schedule_id"] = schedule_id
    if schedule_date is not None:
        entry["schedule_date"] = schedule_date
    if error is not None:
        entry["error"] = error
    else:
        entry.pop("error", None)
    journal.put(key, entry)
