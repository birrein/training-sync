"""Body-weight domain objects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WeightReading:
    calendar_date: str
    weight_kg: float
    source_type: str | None
    day_delta: int


def format_weight_tag(reading: WeightReading) -> str:
    return f"@ {reading.weight_kg:.1f} bw"
