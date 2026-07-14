"""Pure rendering for ordered Garmin activities in a daily training section."""

from collections.abc import Sequence

from training_sync.domain.activity_classification import classify_activity_type
from training_sync.domain.garmin_activity import GarminActivity


def _duration_text(duration_ms: int) -> str:
    total_tenths = round(duration_ms / 100)
    hours, remainder = divmod(total_tenths, 36_000)
    minutes, remainder = divmod(remainder, 600)
    seconds, tenths = divmod(remainder, 10)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{tenths}"


def _pace_text(duration_ms: int, distance_m: float) -> str:
    total_tenths = round(duration_ms * 10 / distance_m)
    minutes, remainder = divmod(total_tenths, 600)
    seconds, tenths = divmod(remainder, 10)
    return f"{minutes:02d}:{seconds:02d}.{tenths}"


def _activity_tag(type_key: str) -> str:
    return classify_activity_type(type_key).daily_tag


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

    if (
        classify_activity_type(activity.type_key).weightxreps_name == "Running"
        and activity.distance_m
    ):
        lines.append(f"@ Avg Pace: {_pace_text(activity.duration_ms, activity.distance_m)}")

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
