"""Pure rendering for ordered Garmin activities in a daily training section."""

from collections.abc import Sequence

from training_sync.domain.garmin_activity import GarminActivity


def _duration_text(duration_ms: int) -> str:
    seconds = duration_ms / 1000
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{seconds:04.1f}"


def _activity_tag(type_key: str) -> str:
    if "run" in type_key:
        return "Running"
    if "cycl" in type_key:
        return "Cycling"
    return type_key.capitalize()


def _metric_text(value: int | float) -> str:
    return f"{value:g}"


def _render_activity(date: str, activity: GarminActivity) -> str:
    lines = [
        f"- {activity.name}",
        "```text",
        date,
        "",
        f"#{_activity_tag(activity.type_key)}",
    ]
    if activity.distance_m is not None:
        distance_km = activity.distance_m / 1000
        lines.append(f"{distance_km:.2f}km")
    lines.append(f"@ Duration: {_duration_text(activity.duration_ms)}")

    if "run" in activity.type_key and activity.distance_m:
        pace_seconds = activity.duration_ms / 1000 / (activity.distance_m / 1000)
        pace_minutes, pace_seconds = divmod(pace_seconds, 60)
        lines.append(f"@ Avg Pace: {int(pace_minutes):02d}:{pace_seconds:04.1f}")

    metadata = (
        ("Avg HR", activity.average_hr),
        ("Max HR", activity.max_hr),
        ("Training Load", activity.training_load),
        ("Elev Gain", activity.elevation_gain_m),
        ("Avg Power", activity.average_power_w),
        ("Calories", activity.calories),
    )
    lines.extend(f"@ {label}: {_metric_text(value)}" for label, value in metadata if value is not None)
    lines.append("```")
    return "\n".join(lines)


def render_training_activities(date: str, activities: Sequence[GarminActivity]) -> str:
    """Render one replacement payload containing every activity in input order."""

    return "\n\n".join(_render_activity(date, activity) for activity in activities)
