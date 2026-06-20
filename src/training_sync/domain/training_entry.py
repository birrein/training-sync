"""Normalized training log entries."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActivityMetric:
    label: str
    value: str


@dataclass(frozen=True)
class TrainingEntry:
    date: str
    title: str
    activity_type: str
    metrics: list[ActivityMetric] = field(default_factory=list)
    body_weight: float | None = None
    text_block: str | None = None
