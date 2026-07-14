"""Shared Garmin activity classification for rendering and Weight x Reps."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityClassification:
    daily_tag: str
    weightxreps_name: str | None
    local_only: bool = False


_RUNNING = ActivityClassification("Running", "Running")
_CYCLING = ActivityClassification("Cycling", "Cycling")
_STRENGTH = ActivityClassification(
    "Strength_training",
    None,
    local_only=True,
)

_CLASSIFICATIONS = {
    "running": _RUNNING,
    "trail_running": _RUNNING,
    "treadmill_running": _RUNNING,
    "virtual_run": _RUNNING,
    "cycling": _CYCLING,
    "virtual_ride": _CYCLING,
    "ride": _CYCLING,
    "indoor_cycling": _CYCLING,
    "road_biking": _CYCLING,
    "mountain_biking": _CYCLING,
    "walking": ActivityClassification("Walking", "Walking"),
    "swimming": ActivityClassification("Swimming", "Swimming"),
    "lap_swimming": ActivityClassification("Swimming", "Swimming"),
    "rowing": ActivityClassification("Rowing", "Rowing"),
    "indoor_rowing": ActivityClassification("Rowing", "Rowing"),
    "cardio": ActivityClassification("Cardio", "Cardio"),
    "generic_cardio": ActivityClassification("Cardio", "Cardio"),
}


def classify_activity_type(type_key: str) -> ActivityClassification:
    normalized = type_key.casefold().replace("-", "_").replace(" ", "_")
    if normalized == "strength_training":
        return _STRENGTH
    try:
        return _CLASSIFICATIONS[normalized]
    except KeyError as exc:
        raise RuntimeError(f"Unsupported Garmin activity type: {type_key}") from exc
