"""Garmin payload decoding kept at the Garmin adapter boundary."""

from collections.abc import Mapping
from datetime import datetime
from typing import cast

from training_sync.domain.garmin_activity import GarminActivity


def decode_activity(raw: Mapping[str, object]) -> GarminActivity:
    """Decode a Garmin activity-list payload into normalized activity values."""
    activity_type = cast(Mapping[str, object], raw["activityType"])
    start_time = raw.get("startTimeLocal")
    if not isinstance(start_time, str):
        raise ValueError("Garmin startTimeLocal must use YYYY-MM-DD HH:MM:SS")
    try:
        datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError("Garmin startTimeLocal must use YYYY-MM-DD HH:MM:SS") from exc
    return GarminActivity(
        activity_id=int(raw["activityId"]),
        name=str(raw["activityName"]),
        start_time=start_time,
        type_key=str(activity_type["typeKey"]),
        duration_ms=round(float(raw["duration"]) * 1000),
        distance_m=_optional_float(raw.get("distance")),
        average_hr=_optional_int(raw.get("averageHR")),
        max_hr=_optional_int(raw.get("maxHR")),
        elevation_gain_m=_optional_float(raw.get("elevationGain")),
        average_power_w=_optional_int(raw.get("avgPower")),
        calories=_optional_int(raw.get("calories")),
        training_load=_optional_float(raw.get("activityTrainingLoad")),
    )


def _optional_int(value: object | None) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: object | None) -> float | None:
    return None if value is None else float(value)
