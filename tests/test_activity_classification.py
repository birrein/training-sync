import pytest

from training_sync.domain.activity_classification import classify_activity_type


@pytest.mark.parametrize(
    ("type_key", "daily_tag", "weightxreps_name"),
    [
        ("trail_running", "Running", "Running"),
        ("treadmill_running", "Running", "Running"),
        ("virtual_run", "Running", "Running"),
        ("indoor_cycling", "Cycling", "Cycling"),
        ("road_biking", "Cycling", "Cycling"),
        ("mountain_biking", "Cycling", "Cycling"),
    ],
)
def test_known_garmin_family_aliases_are_canonical(type_key, daily_tag, weightxreps_name):
    classification = classify_activity_type(type_key)

    assert classification.daily_tag == daily_tag
    assert classification.weightxreps_name == weightxreps_name
    assert classification.local_only is False


def test_strength_precedence_remains_local_only():
    classification = classify_activity_type("strength_training")

    assert classification.daily_tag == "Strength_training"
    assert classification.weightxreps_name is None
    assert classification.local_only is True


def test_unknown_activity_type_is_explicitly_rejected():
    with pytest.raises(RuntimeError, match="Unsupported Garmin activity type: sky_diving"):
        classify_activity_type("sky_diving")
