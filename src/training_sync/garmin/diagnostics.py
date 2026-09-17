"""Bounded, allowlisted diagnostics for Garmin transport failures."""

from __future__ import annotations

import re
from typing import Any, Mapping


_MAX_REFERENCE_LENGTH = 128
_MAX_TYPE_LENGTH = 80
_STAGES = frozenset(
    {
        "upload",
        "read_back",
        "reconciliation",
        "schedule",
        "update",
        "duplicate",
        "delete",
        "unschedule",
        "unknown",
    }
)
_SAFE_TYPE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,78}(?:Exception|Error)$")
_SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_TYPE_IN_TEXT = re.compile(
    r"['\"]error['\"]\s*:\s*['\"]([A-Za-z][A-Za-z0-9_]{0,78}(?:Exception|Error))['\"]"
)
_REFERENCE_IN_TEXT = re.compile(
    r"['\"](?:errorId|referenceId|reference_id)['\"]\s*:\s*['\"]([^'\"]{1,256})['\"]",
    re.IGNORECASE,
)
_STATUS_IN_TEXT = re.compile(
    r"\b(?:API\s+Error|HTTP(?:\s+Error)?|status(?:\s+code)?)\s*[:=]?\s*([1-5][0-9]{2})\b",
    re.IGNORECASE,
)


def extract_provider_diagnostics(
    error: BaseException,
    *,
    stage: str,
) -> dict[str, Any]:
    """Extract only safe fields from an arbitrary provider exception."""

    normalized_stage = stage if stage in _STAGES else "unknown"
    chain = _exception_chain(error)
    result: dict[str, Any] = {"stage": normalized_stage}

    status = next(
        (candidate for item in reversed(chain) if (candidate := _status_from_exception(item)) is not None),
        None,
    )
    if status is None:
        for item in reversed(chain):
            status_match = _STATUS_IN_TEXT.search(str(item))
            if status_match:
                status = int(status_match.group(1))
                break
    if status is not None:
        result["http_status"] = status

    provider_type = next(
        (
            candidate
            for item in reversed(chain)
            if (candidate := _provider_type_from_exception(item, str(item))) is not None
        ),
        None,
    )
    if provider_type is not None:
        result["provider_error_type"] = provider_type

    reference_id = next(
        (
            candidate
            for item in reversed(chain)
            if (candidate := _reference_from_exception(item, str(item))) is not None
        ),
        None,
    )
    if reference_id is not None:
        result["reference_id"] = reference_id
    return result


def _exception_chain(error: BaseException) -> list[BaseException]:
    result: list[BaseException] = []
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        result.append(current)
        cause = current.__cause__ or current.__context__
        current = cause if isinstance(cause, BaseException) else None
    return result


def sanitize_provider_diagnostics(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Return a journal-safe copy of previously extracted diagnostics."""

    if not isinstance(value, Mapping):
        return None
    stage = value.get("stage")
    if not isinstance(stage, str) or stage not in _STAGES:
        stage = "unknown"
    result: dict[str, Any] = {"stage": stage}
    status = value.get("http_status")
    if isinstance(status, int) and not isinstance(status, bool) and 100 <= status <= 599:
        result["http_status"] = status
    for key in ("provider_error_type", "reference_id"):
        raw = value.get(key)
        if not isinstance(raw, str):
            continue
        candidate = raw[: _MAX_TYPE_LENGTH if key == "provider_error_type" else _MAX_REFERENCE_LENGTH]
        pattern = _SAFE_TYPE if key == "provider_error_type" else _SAFE_REFERENCE
        if pattern.fullmatch(candidate):
            result[key] = candidate
    return result


def format_provider_diagnostics(value: Mapping[str, Any] | None) -> str:
    """Render bounded diagnostics without exposing arbitrary exception text."""

    safe = sanitize_provider_diagnostics(value) or {"stage": "unknown"}
    parts = [f"stage={safe['stage']}"]
    if "http_status" in safe:
        parts.append(f"http_status={safe['http_status']}")
    if "provider_error_type" in safe:
        parts.append(f"provider_error_type={safe['provider_error_type']}")
    if "reference_id" in safe:
        parts.append(f"reference_id={safe['reference_id']}")
    return "provider diagnostic (" + ", ".join(parts) + ")"


def _status_from_exception(error: BaseException) -> int | None:
    for owner in (error, getattr(error, "response", None)):
        if owner is None:
            continue
        for name in ("status_code", "status"):
            value = getattr(owner, name, None)
            if isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599:
                return value
    return None


def _provider_type_from_exception(error: BaseException, raw: str) -> str | None:
    structured = _mapping_value(error, "error")
    if isinstance(structured, str) and _SAFE_TYPE.fullmatch(structured):
        return structured[:_MAX_TYPE_LENGTH]
    match = _TYPE_IN_TEXT.search(raw)
    if match:
        return match.group(1)[:_MAX_TYPE_LENGTH]
    error_type = type(error).__name__
    return error_type if _SAFE_TYPE.fullmatch(error_type) else None


def _reference_from_exception(error: BaseException, raw: str) -> str | None:
    for key in ("errorId", "referenceId", "reference_id"):
        value = _mapping_value(error, key)
        if isinstance(value, str) and _SAFE_REFERENCE.fullmatch(value[:_MAX_REFERENCE_LENGTH]):
            return value[:_MAX_REFERENCE_LENGTH]
    match = _REFERENCE_IN_TEXT.search(raw)
    if not match:
        return None
    candidate = match.group(1)[:_MAX_REFERENCE_LENGTH]
    return candidate if _SAFE_REFERENCE.fullmatch(candidate) else None


def _mapping_value(owner: Any, key: str) -> Any:
    if isinstance(owner, Mapping):
        return owner.get(key)
    response = getattr(owner, "response", None)
    if isinstance(response, Mapping):
        return response.get(key)
    return getattr(owner, key, None)
