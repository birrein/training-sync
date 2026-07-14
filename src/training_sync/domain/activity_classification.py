"""Shared Garmin activity classification for rendering and Weight x Reps."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityClassification:
    daily_tag: str
    weightxreps_name: str | None
    local_only: bool = False


_CLASSIFICATIONS = {
    "running": ActivityClassification("Running", "Running"),
    "cycling": ActivityClassification("Cycling", "Cycling"),
    "virtual_ride": ActivityClassification("Cycling", "Cycling"),
    "walking": ActivityClassification("Walking", "Walking"),
    "swimming": ActivityClassification("Swimming", "Swimming"),
    "lap_swimming": ActivityClassification("Swimming", "Swimming"),
    "rowing": ActivityClassification("Rowing", "Rowing"),
    "indoor_rowing": ActivityClassification("Rowing", "Rowing"),
    "cardio": ActivityClassification("Cardio", "Cardio"),
    "generic_cardio": ActivityClassification("Cardio", "Cardio"),
    "strength_training": ActivityClassification(
        "Strength_training",
        None,
        local_only=True,
    ),
}


def classify_activity_type(type_key: str) -> ActivityClassification:
    normalized = type_key.casefold().replace("-", "_").replace(" ", "_")
    try:
        return _CLASSIFICATIONS[normalized]
    except KeyError as exc:
        raise RuntimeError(f"Unsupported Garmin activity type: {type_key}") from exc
