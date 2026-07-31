from training_sync.intervals.client import IntervalsActivity
from training_sync.intervals.matching import match_activity

def activity(id, external_id=None, **kwargs):
    return IntervalsActivity(str(id), "Ride", "2026-07-29T08:00:00", "Ride", external_id=external_id, moving_time=3600, distance=20, **kwargs)

def test_match_prefers_exact_remote_and_garmin_external_id():
    rows = [activity(1, "123"), activity(2)]
    assert match_activity(activities=rows, remote_id="2").activity.id == "2"
    assert match_activity(activities=rows, garmin_id="123").reason == "exact_external_id"

def test_unique_fallback_records_evidence_and_ambiguity_never_selects():
    one = [activity(1)]
    assert match_activity(activities=one, start_date_local="2026-07-29T08:00:00", activity_type="Ride", moving_time=3600, distance=20).reason == "fallback"
    assert match_activity(activities=one * 2, start_date_local="2026-07-29T08:00:00", activity_type="Ride", moving_time=3600, distance=20).activity is None
