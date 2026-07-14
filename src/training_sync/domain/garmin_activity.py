"""Normalized Garmin activity values used by synchronization."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import cast


def _optional_int(value: object | None) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: object | None) -> float | None:
    return None if value is None else float(value)


@dataclass(frozen=True)
class GarminActivity:
    activity_id: int
    name: str
    start_time: str
    type_key: str
    duration_ms: int
    distance_m: float | None
    average_hr: int | None = None
    max_hr: int | None = None
    elevation_gain_m: float | None = None
    average_power_w: int | None = None
    calories: int | None = None
    training_load: float | None = None

    @classmethod
    def from_garmin(cls, raw: Mapping[str, object]) -> "GarminActivity":
        activity_type = cast(Mapping[str, object], raw["activityType"])
        duration_seconds = float(raw["duration"])
        distance = raw.get("distance")
        start_time = raw.get("startTimeLocal")
        if not isinstance(start_time, str):
            raise ValueError("Garmin startTimeLocal must use YYYY-MM-DD HH:MM:SS")
        try:
            datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError(
                "Garmin startTimeLocal must use YYYY-MM-DD HH:MM:SS"
            ) from exc
        return cls(
            activity_id=int(raw["activityId"]),
            name=str(raw["activityName"]),
            start_time=start_time,
            type_key=str(activity_type["typeKey"]),
            duration_ms=round(duration_seconds * 1000),
            distance_m=float(distance) if distance is not None else None,
            average_hr=_optional_int(raw.get("averageHR")),
            max_hr=_optional_int(raw.get("maxHR")),
            elevation_gain_m=_optional_float(raw.get("elevationGain")),
            average_power_w=_optional_int(raw.get("avgPower")),
            calories=_optional_int(raw.get("calories")),
            training_load=_optional_float(raw.get("activityTrainingLoad")),
        )
