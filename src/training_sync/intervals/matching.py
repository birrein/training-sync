"""Deterministic Intervals replica matching; ambiguity is never a deletion signal."""
from dataclasses import dataclass
from training_sync.intervals.client import IntervalsActivity

@dataclass(frozen=True)
class MatchResult:
    activity: IntervalsActivity | None
    reason: str
    evidence: str

def match_activity(*, activities: list[IntervalsActivity], remote_id: str | None = None,
                   garmin_id: str | None = None, start_date_local: str | None = None,
                   activity_type: str | None = None, moving_time: float | None = None,
                   distance: float | None = None) -> MatchResult:
    if remote_id:
        found = [a for a in activities if a.id == str(remote_id)]
        return MatchResult(found[0] if found else None, "exact_remote_id", f"id={remote_id}")
    if garmin_id:
        found = [a for a in activities if a.external_id == str(garmin_id)]
        if len(found) == 1:
            return MatchResult(found[0], "exact_external_id", f"external_id={garmin_id}")
        if len(found) > 1:
            return MatchResult(None, "ambiguous", f"{len(found)} activities share external_id={garmin_id}")
    candidates = [a for a in activities if (not start_date_local or a.start_date_local == start_date_local)
                  and (not activity_type or a.type.lower() == activity_type.lower())
                  and (moving_time is None or a.moving_time is not None and abs(a.moving_time - moving_time) <= 1)
                  and (distance is None or a.distance is not None and abs(a.distance - distance) <= 1)]
    if len(candidates) == 1:
        return MatchResult(candidates[0], "fallback", "matching local start, type, and objective summary")
    return MatchResult(None, "ambiguous" if candidates else "none",
                       f"{len(candidates)} fallback candidates")
