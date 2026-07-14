from training_sync.domain.garmin_activity import GarminActivity
from training_sync.renderers.garmin_daily import render_training_activities


DATE = "2026-07-03"


def activity(
    activity_id: int,
    name: str,
    type_key: str,
    *,
    duration_ms: int,
    distance_m: float | None,
    **metadata,
) -> GarminActivity:
    return GarminActivity(
        activity_id=activity_id,
        name=name,
        start_time=f"{DATE} 0{activity_id}:00:00",
        type_key=type_key,
        duration_ms=duration_ms,
        distance_m=distance_m,
        **metadata,
    )


def test_render_training_activities_combines_every_activity_in_input_order():
    activities = [
        activity(
            1,
            "Morning Strength",
            "strength_training",
            duration_ms=2_700_000,
            distance_m=None,
        ),
        activity(
            2,
            "Morning Run",
            "running",
            duration_ms=1_500_500,
            distance_m=5_000,
            average_hr=148,
            max_hr=171,
        ),
        activity(
            3,
            "Evening Ride",
            "cycling",
            duration_ms=3_620_000,
            distance_m=27_950,
            elevation_gain_m=158.5,
            average_power_w=177,
            calories=530,
            training_load=84.2,
        ),
        activity(
            4,
            "Recovery Cardio",
            "cardio",
            duration_ms=900_000,
            distance_m=None,
        ),
    ]

    rendered = render_training_activities(DATE, activities)

    positions = [rendered.index(item.name) for item in activities]
    assert positions == sorted(positions)
    assert rendered.count(DATE) == len(activities)
    assert rendered.count("```text") == len(activities)
    assert "## 🏃 Training" not in rendered
    for item in activities:
        assert rendered.count(f"- {item.name}") == 1


def test_render_training_activities_formats_real_metrics_and_omits_missing_distance():
    run = activity(
        1,
        "Morning Run",
        "running",
        duration_ms=1_500_500,
        distance_m=5_000,
        average_hr=148,
        max_hr=171,
    )
    ride = activity(
        2,
        "Evening Ride",
        "cycling",
        duration_ms=3_620_000,
        distance_m=27_950,
        elevation_gain_m=158.5,
        average_power_w=177,
        calories=530,
        training_load=84.2,
    )
    duration_only = activity(
        3,
        "Recovery Cardio",
        "cardio",
        duration_ms=900_000,
        distance_m=None,
    )

    rendered = render_training_activities(DATE, [run, ride, duration_only])
    duration_only_block = rendered[rendered.index(duration_only.name) :]

    assert "5.00km" in rendered
    assert "27.95km" in rendered
    assert "@ Duration: 01:00:20.0" in rendered
    assert "@ Avg Pace: 05:00.1" in rendered
    assert "@ Avg HR: 148" in rendered
    assert "@ Max HR: 171" in rendered
    assert "@ Training Load: 84.2" in rendered
    assert "@ Elev Gain: 158.5" in rendered
    assert "@ Avg Power: 177" in rendered
    assert "@ Calories: 530" in rendered
    assert "@ Duration: 00:15:00.0" in duration_only_block
    assert "km" not in duration_only_block
