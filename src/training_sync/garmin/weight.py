"""Helpers for reading Garmin body-weight entries."""

from datetime import date, timedelta
from typing import Any

from garminconnect import Garmin

from training_sync.domain.body_weight import WeightReading, format_weight_tag

GRAMS_PER_KG = 1000.0


def find_nearest_weight(
    client: Garmin,
    target_date: str,
    window_days: int = 14,
) -> WeightReading | None:
    """Return the closest Garmin weigh-in to target_date."""
    target = date.fromisoformat(target_date)
    start = (target - timedelta(days=window_days)).isoformat()
    end = (target + timedelta(days=window_days)).isoformat()
    response = client.get_weigh_ins(start, end)

    readings = [
        reading
        for raw in _weight_records(response)
        if (reading := _to_weight_reading(raw, target)) is not None
    ]
    if not readings:
        return None

    return min(readings, key=lambda reading: (abs(reading.day_delta), reading.day_delta))


def print_weight_tag(client: Garmin, target_date: str) -> bool:
    """Print the closest body-weight tag for target_date."""
    reading = find_nearest_weight(client, target_date)
    if reading is None:
        print(f"No Garmin weigh-in found near {target_date}")
        return False

    print(format_weight_tag(reading))
    return True


def _weight_records(response: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for summary in response.get("dailyWeightSummaries", []):
        records.extend(summary.get("allWeightMetrics") or [])
        latest = summary.get("latestWeight")
        if latest:
            records.append(latest)

    for key in ("previousDateWeight", "nextDateWeight"):
        record = response.get(key)
        if record:
            records.append(record)

    records.extend(response.get("dateWeightList") or [])
    return records


def _to_weight_reading(
    record: dict[str, Any],
    target: date,
) -> WeightReading | None:
    calendar_date = record.get("calendarDate")
    weight_grams = record.get("weight")
    if not calendar_date or weight_grams is None:
        return None

    reading_date = date.fromisoformat(calendar_date)
    return WeightReading(
        calendar_date=calendar_date,
        weight_kg=float(weight_grams) / GRAMS_PER_KG,
        source_type=record.get("sourceType"),
        day_delta=(reading_date - target).days,
    )
