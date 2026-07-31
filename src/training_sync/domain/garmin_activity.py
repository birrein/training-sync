"""Normalized Garmin activity values used by synchronization."""

from dataclasses import dataclass
from collections.abc import Mapping


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
        # Compatibility entry point; decoding itself belongs to the adapter.
        from training_sync.garmin.activity import decode_activity

        return decode_activity(raw)
