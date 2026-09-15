"""Verified, recoverable publication of planned Garmin workouts.

The use case owns lifecycle and recovery decisions.  Garmin DTO construction
and semantic step shape remain in :mod:`training_sync.garmin.planned_workouts`.
All mutations require ``authorized=True``; the default path is an offline
preview and does not require a client, a token, or a vault.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, asdict
from datetime import date
import fcntl
import hashlib
import json
from pathlib import Path
import threading
from typing import Any, Iterable, Mapping

from training_sync.config import planned_workout_journal_path
from training_sync.domain.planned_workout import (
    PlannedWorkout,
    planned_workout_from_dict,
)
from training_sync.garmin.planned_workouts import (
    GarminWorkoutProjection,
    project_planned_workout,
)
from training_sync.garmin.workout_steps import (
    RepeatGroupLayout,
    WorkoutStepDecodeError,
    decode_workout_steps,
)


class PublicationError(RuntimeError):
    """Base error for an unsafe or unsuccessful planned publication."""


class PublicationConflictError(PublicationError):
    """Raised when an existing journal key has different execution content."""


@dataclass(frozen=True)
class PublicationResult:
    """Separate template and calendar states returned by publication."""

    state: str
    template_state: str
    schedule_state: str
    workout_id: int | str | None = None
    schedule_id: int | str | None = None
    schedule_date: str | None = None
    verified: bool = False
    scheduled: bool = False
    reused: bool = False
    marker: str | None = None
    preview: str | None = None
    error: str | None = None
    verification_errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_journal_locks_guard = threading.Lock()
_journal_locks: dict[str, threading.RLock] = {}


def publish_workout(
    client: Any | None,
    workout: PlannedWorkout | Mapping[str, Any],
    *,
    authorized: bool = False,
    yes: bool | None = None,
    schedule_date: str | date | None = None,
    account: str | None = None,
    journal_path: Path | str | None = "__default__",
    max_steps: int | None = None,
) -> PublicationResult:
    """Preview or publish one planned workout with verified recovery.

    ``schedule_date`` is deliberately independent from ``workout.date``.  A
    plan date is provenance/input context; only this explicit argument creates
    a calendar occurrence.  A successful upload is never reported as device
    delivery.
    """

    if yes is not None:
        authorized = yes
    normalized = _coerce_workout(workout)
    projection = project_planned_workout(normalized, max_steps=max_steps)
    marker = build_publication_marker(normalized)
    requested_date = _normalize_schedule_date(schedule_date)

    if not authorized:
        return PublicationResult(
            state="preview",
            template_state="not_attempted",
            schedule_state="not_requested" if requested_date is None else "not_attempted",
            schedule_date=requested_date,
            marker=marker,
            preview=projection.preview,
        )
    if client is None:
        raise PublicationError("an authenticated Garmin client is required with --yes")

    path = _resolve_journal_path(journal_path)
    account_key = _account_key(client, account)
    lock_key = f"{account_key}\0{normalized.key}"
    with _publication_lock(path, lock_key):
        journal = _Journal(path)
        entry = journal.get(lock_key)
        execution_hash = normalized.execution_hash()
        if entry is not None and entry.get("execution_hash") != execution_hash:
            raise PublicationConflictError(
                f"planned workout key '{normalized.key}' already has different content"
            )

        workout_id: int | str | None = None
        reused = False
        if entry is not None:
            workout_id = _value_or_none(entry.get("workout_id"))
            reused = workout_id is not None

        if workout_id is None and entry is not None and entry.get("state") in {
            "uploading",
            "uncertain",
        }:
            reconciliation = _reconcile_upload(
                client,
                projection,
                marker,
                require_layout=bool(entry.get("strict_layout", False)),
            )
            if reconciliation.state == "uncertain":
                _save_entry(
                    journal,
                    lock_key,
                    normalized,
                    marker,
                    state="uncertain",
                    error=reconciliation.error,
                )
                return _result_with_reconciliation(
                    reconciliation,
                    projection,
                    marker,
                    requested_date,
                )
            workout_id = reconciliation.workout_id
            reused = True
            _save_entry(
                journal,
                lock_key,
                normalized,
                marker,
                state="uploaded",
                workout_id=workout_id,
            )

        if workout_id is not None:
            verification = _verify_remote_template(
                client,
                workout_id,
                projection,
                require_layout=bool(entry.get("strict_layout", False)) if entry else False,
            )
            if verification[0] is not True:
                errors = verification[1]
                _save_entry(
                    journal,
                    lock_key,
                    normalized,
                    marker,
                    state="verification_failed",
                    workout_id=workout_id,
                    error="; ".join(errors),
                )
                return PublicationResult(
                    state="verification_failed",
                    template_state="verification_failed",
                    schedule_state="not_attempted" if requested_date else "not_requested",
                    workout_id=workout_id,
                    schedule_date=requested_date,
                    verified=False,
                    reused=reused,
                    marker=marker,
                    preview=projection.preview,
                    error="; ".join(errors),
                    verification_errors=tuple(errors),
                )
            template_state = "verified"
        else:
            payload = _payload_with_marker(projection, marker)
            _save_entry(
                journal,
                lock_key,
                normalized,
                marker,
                state="uploading",
                desired_payload_hash=_payload_hash(payload),
                strict_layout=True,
            )
            try:
                response = _upload_workout(client, payload)
                workout_id = _extract_workout_id(response)
                if workout_id is None:
                    raise TimeoutError("Garmin upload returned no workout ID")
                # Persist the returned ID before read-back: a later retry can
                # verify/reuse it even if this process exits now.
                _save_entry(
                    journal,
                    lock_key,
                    normalized,
                    marker,
                    state="uploaded",
                    workout_id=workout_id,
                    desired_payload_hash=_payload_hash(payload),
                )
            except Exception as exc:
                reconciliation = _reconcile_upload(
                    client,
                    projection,
                    marker,
                    require_layout=True,
                )
                if reconciliation.state == "verified":
                    workout_id = reconciliation.workout_id
                    reused = True
                    _save_entry(
                        journal,
                        lock_key,
                        normalized,
                        marker,
                        state="uploaded",
                        workout_id=workout_id,
                        error=f"upload response uncertain: {type(exc).__name__}",
                    )
                else:
                    message = (
                        f"upload outcome uncertain after {type(exc).__name__}: "
                        f"{reconciliation.error}"
                    )
                    _save_entry(
                        journal,
                        lock_key,
                        normalized,
                        marker,
                        state="uncertain",
                        error=message,
                    )
                    return PublicationResult(
                        state="uncertain",
                        template_state="uncertain",
                        schedule_state="not_attempted" if requested_date else "not_requested",
                        schedule_date=requested_date,
                        verified=False,
                        marker=marker,
                        preview=projection.preview,
                        error=message,
                    )

            verification = _verify_remote_template(client, workout_id, projection)
            if verification[0] is not True:
                errors = verification[1]
                _save_entry(
                    journal,
                    lock_key,
                    normalized,
                    marker,
                    state="verification_failed",
                    workout_id=workout_id,
                    error="; ".join(errors),
                )
                return PublicationResult(
                    state="verification_failed",
                    template_state="verification_failed",
                    schedule_state="not_attempted" if requested_date else "not_requested",
                    workout_id=workout_id,
                    schedule_date=requested_date,
                    marker=marker,
                    preview=projection.preview,
                    error="; ".join(errors),
                    verification_errors=tuple(errors),
                )
            template_state = "verified"
            _save_entry(
                journal,
                lock_key,
                normalized,
                marker,
                state="template_verified",
                workout_id=workout_id,
            )

        if requested_date is None:
            return PublicationResult(
                state="verified",
                template_state=template_state,
                schedule_state="not_requested",
                workout_id=workout_id,
                verified=True,
                reused=reused,
                marker=marker,
                preview=projection.preview,
            )

        prior_schedule_id = _value_or_none(entry.get("schedule_id")) if entry else None
        prior_schedule_date = entry.get("schedule_date") if entry else None
        if prior_schedule_id is not None and prior_schedule_date == requested_date:
            if _verify_schedule(client, prior_schedule_id, workout_id, requested_date)[0]:
                return PublicationResult(
                    state="scheduled",
                    template_state="verified",
                    schedule_state="verified",
                    workout_id=workout_id,
                    schedule_id=prior_schedule_id,
                    schedule_date=requested_date,
                    verified=True,
                    scheduled=True,
                    reused=True,
                    marker=marker,
                    preview=projection.preview,
                )

        _save_entry(
            journal,
            lock_key,
            normalized,
            marker,
            state="scheduling",
            workout_id=workout_id,
            schedule_date=requested_date,
        )
        try:
            schedule_response = _schedule_workout(client, workout_id, requested_date)
            schedule_id = _extract_schedule_id(schedule_response)
            if schedule_id is None:
                schedule_id = _find_schedule_id(client, workout_id, requested_date)
            if schedule_id is None:
                raise RuntimeError("Garmin returned no schedule ID for the requested date")
        except Exception as exc:
            _save_entry(
                journal,
                lock_key,
                normalized,
                marker,
                state="schedule_failed",
                workout_id=workout_id,
                schedule_date=requested_date,
                error=_safe_error(exc),
            )
            return PublicationResult(
                state="partial",
                template_state="verified",
                schedule_state="failed",
                workout_id=workout_id,
                schedule_date=requested_date,
                verified=True,
                marker=marker,
                preview=projection.preview,
                error=_safe_error(exc),
            )

        _save_entry(
            journal,
            lock_key,
            normalized,
            marker,
            state="scheduled_unverified",
            workout_id=workout_id,
            schedule_id=schedule_id,
            schedule_date=requested_date,
        )
        schedule_verification = _verify_schedule(
            client, schedule_id, workout_id, requested_date
        )
        if not schedule_verification[0]:
            error = "; ".join(schedule_verification[1])
            _save_entry(
                journal,
                lock_key,
                normalized,
                marker,
                state="schedule_verification_failed",
                workout_id=workout_id,
                schedule_id=schedule_id,
                schedule_date=requested_date,
                error=error,
            )
            return PublicationResult(
                state="partial",
                template_state="verified",
                schedule_state="verification_failed",
                workout_id=workout_id,
                schedule_id=schedule_id,
                schedule_date=requested_date,
                verified=True,
                marker=marker,
                preview=projection.preview,
                error=error,
                verification_errors=tuple(schedule_verification[1]),
            )
        _save_entry(
            journal,
            lock_key,
            normalized,
            marker,
            state="scheduled",
            workout_id=workout_id,
            schedule_id=schedule_id,
            schedule_date=requested_date,
        )
        return PublicationResult(
            state="scheduled",
            template_state="verified",
            schedule_state="verified",
            workout_id=workout_id,
            schedule_id=schedule_id,
            schedule_date=requested_date,
            verified=True,
            scheduled=True,
            reused=reused,
            marker=marker,
            preview=projection.preview,
        )


def publish_planned_workout(*args: Any, **kwargs: Any) -> PublicationResult:
    """Descriptive alias for :func:`publish_workout`."""

    return publish_workout(*args, **kwargs)


def build_publication_marker(workout: PlannedWorkout) -> str:
    """Build an opaque marker containing no source prose or secret values."""

    key_digest = hashlib.sha256(workout.key.encode("utf-8")).hexdigest()
    return (
        "training-sync:plan-sha256="
        f"{key_digest}:execution-sha256={workout.execution_hash()}"
    )


def verify_saved_workout(
    projection: GarminWorkoutProjection,
    saved: Mapping[str, Any],
    *,
    require_layout: bool = True,
) -> tuple[bool, tuple[str, ...]]:
    """Compare expanded semantics and, for new writes, the requested layout."""

    errors: list[str] = []
    try:
        decoded = decode_workout_steps(saved)
    except WorkoutStepDecodeError as exc:
        return False, (f"Garmin workout step tree is unsupported: {exc}",)
    saved_steps = list(decoded.steps)
    if saved.get("workoutName") != projection.payload.get("workoutName"):
        errors.append("workoutName mismatch")
    if _nested_key(saved, "sportType", "sportTypeKey") != _nested_key(
        projection.payload, "sportType", "sportTypeKey"
    ):
        errors.append("sportType mismatch")
    expected_steps = list(projection.steps)
    if len(saved_steps) != len(expected_steps):
        errors.append(
            f"step count mismatch: expected {len(expected_steps)}, saved {len(saved_steps)}"
        )
    for index, (expected, actual) in enumerate(
        zip(expected_steps, saved_steps), start=1
    ):
        errors.extend(_compare_step(index, expected, actual))
    if require_layout:
        errors.extend(_compare_repeat_layout(projection.repeat_groups, decoded.repeat_groups))
    return not errors, tuple(errors)


def _verify_remote_template(
    client: Any,
    workout_id: int | str,
    projection: GarminWorkoutProjection,
    *,
    require_layout: bool = True,
) -> tuple[bool, tuple[str, ...]]:
    try:
        saved = _get_workout(client, workout_id)
    except Exception as exc:
        return False, (f"Garmin workout read-back failed: {_safe_error(exc)}",)
    if not isinstance(saved, Mapping):
        return False, ("Garmin workout read-back was not an object",)
    return verify_saved_workout(projection, saved, require_layout=require_layout)


def _compare_repeat_layout(
    expected: tuple[RepeatGroupLayout, ...],
    actual: tuple[RepeatGroupLayout, ...],
) -> list[str]:
    """Compare the compact representation after expanded semantics match."""

    if len(expected) != len(actual):
        return [
            "repeat group representation mismatch: "
            f"expected {len(expected)} groups, saved {len(actual)}"
        ]
    errors: list[str] = []
    for group_index, (expected_group, actual_group) in enumerate(
        zip(expected, actual), start=1
    ):
        prefix = f"repeat group {group_index}"
        if expected_group.start_index != actual_group.start_index:
            errors.append(f"{prefix} position mismatch")
        if expected_group.iterations != actual_group.iterations:
            errors.append(
                f"{prefix} iteration count mismatch: expected "
                f"{expected_group.iterations}, saved {actual_group.iterations}"
            )
        if expected_group.skip_last_rest_step != actual_group.skip_last_rest_step:
            errors.append(f"{prefix} skipLastRestStep mismatch")
        if expected_group.group_type != actual_group.group_type:
            errors.append(f"{prefix} type mismatch")
        if expected_group.step_type_key != actual_group.step_type_key:
            errors.append(f"{prefix} step type mismatch")
        if len(expected_group.child_steps) != len(actual_group.child_steps):
            errors.append(f"{prefix} child count mismatch")
            continue
        for child_index, (expected_child, actual_child) in enumerate(
            zip(expected_group.child_steps, actual_group.child_steps), start=1
        ):
            for detail in _compare_step(
                child_index, expected_child, actual_child
            ):
                errors.append(f"{prefix} child {child_index}: {detail}")
    return errors


def _compare_step(
    index: int,
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    expected_type = _nested_key(expected, "stepType", "stepTypeKey")
    actual_type = _nested_key(actual, "stepType", "stepTypeKey")
    if expected_type != actual_type:
        errors.append(f"step {index} type mismatch: expected {expected_type}, saved {actual_type}")

    expected_condition = _nested_key(expected, "endCondition", "conditionTypeKey")
    actual_condition = _nested_key(actual, "endCondition", "conditionTypeKey")
    if expected_condition != actual_condition:
        errors.append(
            f"step {index} termination mismatch: expected {expected_condition}, saved {actual_condition}"
        )
    if not _same_number(expected.get("endConditionValue"), actual.get("endConditionValue")):
        errors.append(f"step {index} termination value mismatch")

    expected_target = _nested_key(expected, "targetType", "workoutTargetTypeKey")
    actual_target = _nested_key(actual, "targetType", "workoutTargetTypeKey")
    if expected_target != actual_target:
        errors.append(f"step {index} target type mismatch")
    for key in ("targetValueOne", "targetValueTwo"):
        if not _same_number(expected.get(key), actual.get(key)):
            errors.append(f"step {index} {key} mismatch")
    if expected.get("targetValueUnit") != actual.get("targetValueUnit"):
        errors.append(f"step {index} target unit mismatch")

    for key in ("category", "exerciseName", "repetitionCount"):
        if expected.get(key) != actual.get(key):
            errors.append(f"step {index} {key} mismatch")
    if not _same_weight(expected, actual):
        errors.append(f"step {index} load value/unit mismatch")
    expected_description = str(expected.get("description") or "").strip()
    actual_description = str(actual.get("description") or "").strip()
    for key in ("weightBasis", "loadKind", "side"):
        expected_value = expected.get(key)
        actual_value = actual.get(key)
        if actual_value is None and expected_value is not None:
            if not _description_carries_semantic(
                key, expected_value, expected_description, actual_description
            ):
                errors.append(f"step {index} {key} mismatch")
        elif expected_value != actual_value:
            errors.append(f"step {index} {key} mismatch")

    if expected_description and expected_description not in actual_description:
        errors.append(f"step {index} description/side semantics mismatch")
    return errors


def _description_carries_semantic(
    key: str,
    value: Any,
    expected_description: str,
    actual_description: str,
) -> bool:
    """Accept provider read-back that omits our optional semantic fields.

    Garmin may retain the human description while dropping adapter-only
    fields such as ``weightBasis``.  The description is the portable semantic
    channel; an explicitly different provider value still fails verification.
    """

    if not actual_description:
        return False
    if key == "weightBasis":
        phrase = "per hand" if value == "per_hand" else "total"
        return phrase in actual_description.lower()
    if key == "loadKind":
        if value == "mass":
            return "kg" in actual_description.lower()
        return str(value).lower() in actual_description.lower()
    if key == "side":
        return f"{value} side" in actual_description.lower()
    return False


def _same_weight(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> bool:
    expected_value = expected.get("weightValue")
    actual_value = actual.get("weightValue")
    if expected_value is None or actual_value is None:
        return expected_value is None and actual_value is None
    expected_unit = expected.get("weightUnit")
    actual_unit = actual.get("weightUnit")
    expected_grams = _weight_in_grams(expected_value, expected_unit)
    actual_grams = _weight_in_grams(actual_value, actual_unit)
    return expected_grams is not None and actual_grams is not None and math_close(
        expected_grams, actual_grams
    )


def _weight_in_grams(value: Any, unit: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    unit_text = str(unit or "").lower()
    if unit_text in {"kg", "kilogram", "kilograms"}:
        result *= 1000
    return result


def math_close(left: float, right: float) -> bool:
    return abs(left - right) <= 0.001


def _reconcile_upload(
    client: Any,
    projection: GarminWorkoutProjection,
    marker: str,
    *,
    require_layout: bool = False,
) -> PublicationResult:
    try:
        candidates, incomplete = _list_workouts(client)
    except Exception as exc:
        return PublicationResult(
            state="uncertain",
            template_state="uncertain",
            schedule_state="not_attempted",
            error=f"read-only reconciliation failed: {_safe_error(exc)}",
        )
    exact_ids: list[int | str] = []
    for candidate in candidates:
        if marker not in str(candidate.get("description") or ""):
            continue
        workout_id = _extract_workout_id(candidate)
        if workout_id is None:
            continue
        saved = candidate
        try:
            fetched = _get_workout(client, workout_id)
            if isinstance(fetched, Mapping):
                saved = fetched
        except Exception:
            pass
        if verify_saved_workout(projection, saved, require_layout=require_layout)[0]:
            exact_ids.append(workout_id)
    if len(exact_ids) == 1 and not (incomplete and len(exact_ids) > 1):
        return PublicationResult(
            state="verified",
            template_state="verified",
            schedule_state="not_requested",
            workout_id=exact_ids[0],
        )
    if len(exact_ids) == 0:
        reason = "no exact marker and semantic match found"
    else:
        reason = f"{len(exact_ids)} exact marker and semantic matches found"
    if incomplete:
        reason += "; bounded inventory may be incomplete"
    return PublicationResult(
        state="uncertain",
        template_state="uncertain",
        schedule_state="not_attempted",
        error=reason,
    )


def _result_with_reconciliation(
    reconciliation: PublicationResult,
    projection: GarminWorkoutProjection,
    marker: str,
    requested_date: str | None,
) -> PublicationResult:
    return PublicationResult(
        state=reconciliation.state,
        template_state=reconciliation.template_state,
        schedule_state="not_attempted" if requested_date else "not_requested",
        workout_id=reconciliation.workout_id,
        schedule_date=requested_date,
        marker=marker,
        preview=projection.preview,
        error=reconciliation.error,
        verified=False,
    )


def _extract_steps(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return the bounded expanded sequence from a supported step tree."""

    return list(decode_workout_steps(payload).steps)


def _nested_key(value: Mapping[str, Any], parent: str, key: str) -> Any:
    nested = value.get(parent)
    return nested.get(key) if isinstance(nested, Mapping) else None


def _same_number(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return expected is None and actual is None
    try:
        return math_close(float(expected), float(actual))
    except (TypeError, ValueError):
        return expected == actual


def _coerce_workout(value: PlannedWorkout | Mapping[str, Any]) -> PlannedWorkout:
    if isinstance(value, PlannedWorkout):
        return value
    if isinstance(value, Mapping):
        return planned_workout_from_dict(dict(value))
    raise TypeError("workout must be a PlannedWorkout or a planned-workout object")


def _normalize_schedule_date(value: str | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise ValueError("schedule_date must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError("schedule_date must be an ISO date") from exc


def _resolve_journal_path(value: Path | str | None) -> Path | None:
    if value == "__default__":
        return planned_workout_journal_path()
    if value is None:
        return None
    return Path(value).expanduser()


def _account_key(client: Any, account: str | None) -> str:
    if account and account.strip():
        return account.strip()
    for name in ("account_id", "username", "email"):
        value = getattr(client, name, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return "default"


def _payload_with_marker(
    projection: GarminWorkoutProjection,
    marker: str,
) -> dict[str, Any]:
    payload = deepcopy(projection.payload)
    current = str(payload.get("description") or "").strip()
    payload["description"] = f"{current} | {marker}" if current else marker
    return payload


def _payload_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _save_entry(
    journal: "_Journal",
    key: str,
    workout: PlannedWorkout,
    marker: str,
    *,
    state: str,
    workout_id: int | str | None = None,
    schedule_id: int | str | None = None,
    schedule_date: str | None = None,
    desired_payload_hash: str | None = None,
    strict_layout: bool | None = None,
    error: str | None = None,
) -> None:
    existing = journal.get(key) or {}
    entry = {
        **existing,
        "account_plan_key": key,
        "plan_key": workout.key,
        "execution_hash": workout.execution_hash(),
        "marker": marker,
        "state": state,
    }
    if workout_id is not None:
        entry["workout_id"] = workout_id
    if schedule_id is not None:
        entry["schedule_id"] = schedule_id
    if schedule_date is not None:
        entry["schedule_date"] = schedule_date
    if desired_payload_hash is not None:
        entry["desired_payload_hash"] = desired_payload_hash
    if strict_layout is not None:
        entry["strict_layout"] = strict_layout
    if error is not None:
        entry["error"] = error
    else:
        entry.pop("error", None)
    journal.put(key, entry)


def _upload_workout(client: Any, payload: Mapping[str, Any]) -> Any:
    method = getattr(client, "upload_workout", None)
    if method is None:
        method = getattr(client, "create_workout", None)
    if method is None:
        raise PublicationError("Garmin client does not support workout upload")
    return method(dict(payload))


def _get_workout(client: Any, workout_id: int | str) -> Any:
    method = getattr(client, "get_workout_by_id", None)
    if method is None:
        method = getattr(client, "get_workout", None)
    if method is None:
        raise PublicationError("Garmin client does not support workout read-back")
    return method(workout_id)


def _schedule_workout(client: Any, workout_id: int | str, schedule_date: str) -> Any:
    method = getattr(client, "schedule_workout", None)
    if method is None:
        raise PublicationError("Garmin client does not support workout scheduling")
    return method(workout_id, schedule_date)


def _extract_workout_id(value: Any) -> int | str | None:
    if isinstance(value, (int, str)) and not isinstance(value, bool):
        return value
    if not isinstance(value, Mapping):
        return None
    for key in ("workoutId", "workoutID", "workout_id", "id"):
        candidate = value.get(key)
        if isinstance(candidate, (int, str)) and not isinstance(candidate, bool):
            return candidate
    for key in ("workout", "workoutSummary"):
        nested = value.get(key)
        candidate = _extract_workout_id(nested)
        if candidate is not None:
            return candidate
    return None


def _extract_schedule_id(value: Any) -> int | str | None:
    if isinstance(value, (int, str)) and not isinstance(value, bool):
        return value
    if not isinstance(value, Mapping):
        return None
    for key in (
        "scheduleId",
        "scheduleID",
        "schedule_id",
        "workoutScheduleId",
        "workoutScheduleID",
        "id",
    ):
        candidate = value.get(key)
        if isinstance(candidate, (int, str)) and not isinstance(candidate, bool):
            return candidate
    for key in ("schedule", "workoutSchedule"):
        candidate = _extract_schedule_id(value.get(key))
        if candidate is not None:
            return candidate
    return None


def _list_workouts(client: Any, *, max_pages: int = 3, page_size: int = 100) -> tuple[list[Mapping[str, Any]], bool]:
    method = getattr(client, "get_workouts", None)
    if method is None:
        raise PublicationError("Garmin client does not support bounded workout inventory")
    result: list[Mapping[str, Any]] = []
    incomplete = False
    for page in range(max_pages):
        try:
            response = method(start=page * page_size, limit=page_size)
        except TypeError:
            try:
                response = method(page=page, limit=page_size)
            except TypeError:
                response = method()
            page = max_pages - 1
        values, response_incomplete = _workout_items(response)
        result.extend(values)
        incomplete = incomplete or response_incomplete
        if len(values) < page_size:
            break
        if page == max_pages - 1:
            incomplete = True
    return result, incomplete


def _workout_items(value: Any) -> tuple[list[Mapping[str, Any]], bool]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)], False
    if isinstance(value, Mapping):
        for key in ("workouts", "items", "results", "data"):
            items = value.get(key)
            if isinstance(items, list):
                incomplete = bool(value.get("incomplete"))
                return [item for item in items if isinstance(item, Mapping)], incomplete
    return [], False


def _find_schedule_id(client: Any, workout_id: int | str, schedule_date: str) -> int | str | None:
    method = getattr(client, "get_scheduled_workouts", None)
    if method is None:
        return None
    parsed = date.fromisoformat(schedule_date)
    try:
        response = method(parsed.year, parsed.month)
    except TypeError:
        response = method(schedule_date, schedule_date)
    for item in _calendar_items(response):
        if _schedule_matches(item, workout_id, schedule_date):
            return _extract_schedule_id(item)
    return None


def _verify_schedule(
    client: Any,
    schedule_id: int | str,
    workout_id: int | str,
    schedule_date: str,
) -> tuple[bool, tuple[str, ...]]:
    method = getattr(client, "get_scheduled_workout_by_id", None)
    if method is None:
        return False, ("Garmin schedule read-back is unavailable",)
    try:
        saved = method(schedule_id)
    except Exception as exc:
        return False, (f"schedule read-back failed: {_safe_error(exc)}",)
    if not isinstance(saved, Mapping):
        return False, ("schedule read-back was not an object",)
    errors: list[str] = []
    saved_date = _schedule_date(saved)
    if saved_date != schedule_date:
        errors.append(f"scheduled date mismatch: expected {schedule_date}, saved {saved_date}")
    saved_workout_id = _schedule_workout_id(saved)
    if saved_workout_id is None or str(saved_workout_id) != str(workout_id):
        errors.append("scheduled workout ID mismatch")
    return not errors, tuple(errors)


def _calendar_items(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, list):
        return (item for item in value if isinstance(item, Mapping))
    if isinstance(value, Mapping):
        for key in ("scheduledWorkouts", "workouts", "items", "results", "data"):
            items = value.get(key)
            if isinstance(items, list):
                return (item for item in items if isinstance(item, Mapping))
    return ()


def _schedule_matches(value: Mapping[str, Any], workout_id: int | str, schedule_date: str) -> bool:
    return (
        _schedule_date(value) == schedule_date
        and str(_schedule_workout_id(value)) == str(workout_id)
    )


def _schedule_date(value: Mapping[str, Any]) -> str | None:
    for key in ("date", "scheduledDate", "calendarDate", "scheduleDate"):
        raw = value.get(key)
        if isinstance(raw, str):
            return raw[:10]
    return None


def _schedule_workout_id(value: Mapping[str, Any]) -> int | str | None:
    for key in ("workoutId", "workoutID", "workout_id"):
        candidate = value.get(key)
        if isinstance(candidate, (int, str)) and not isinstance(candidate, bool):
            return candidate
    for key in ("workout", "workoutSummary"):
        candidate = _extract_workout_id(value.get(key))
        if candidate is not None:
            return candidate
    return None


def _value_or_none(value: Any) -> int | str | None:
    return value if isinstance(value, (int, str)) and not isinstance(value, bool) else None


def _safe_error(error: Exception) -> str:
    # Do not expose request bodies, tokens, source prose or credentials in
    # local journal/output.  Provider exception text is intentionally reduced.
    return type(error).__name__


class _Journal:
    def __init__(self, path: Path | None):
        self.path = path

    def _read(self) -> dict[str, Any]:
        if self.path is None or not self.path.exists():
            return {"entries": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PublicationError(f"planned-workout journal cannot be read: {type(exc).__name__}") from exc
        if not isinstance(value, dict) or not isinstance(value.get("entries", {}), dict):
            raise PublicationError("planned-workout journal has invalid structure")
        return value

    def get(self, key: str) -> dict[str, Any] | None:
        return self._read().get("entries", {}).get(key)

    def put(self, key: str, entry: Mapping[str, Any]) -> None:
        if self.path is None:
            return
        document = self._read()
        document.setdefault("entries", {})[key] = dict(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.tmp-{threading.get_ident()}")
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)


@contextmanager
def _publication_lock(path: Path | None, key: str):
    if path is None:
        yield
        return
    lock_id = str(path.resolve()) + "\0" + key
    with _journal_locks_guard:
        process_lock = _journal_locks.setdefault(lock_id, threading.RLock())
    with process_lock:
        lock_path = path.with_name(f".{path.name}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
