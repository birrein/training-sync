from training_sync.domain.training import (
    Provenance,
    StrengthWorkout,
    StrengthWorkoutImport,
    promote_verified_strength_import,
)


def test_screenshot_derived_import_is_not_a_completed_activity_before_readback():
    imported = StrengthWorkoutImport(
        date="2026-07-28",
        workout=StrengthWorkout(exercises=()),
        provenance=Provenance(provider="fitbod_screenshot", reference="shot:1"),
        title="Upper Body",
    )

    assert imported.provenance.verified is False
    assert not hasattr(imported, "local_start")


def test_verified_garmin_readback_promotes_import_to_completed_activity():
    imported = StrengthWorkoutImport(
        date="2026-07-28",
        workout=StrengthWorkout(exercises=()),
        provenance=Provenance(provider="fitbod_screenshot", reference="shot:1"),
        title="Upper Body",
    )

    completed = promote_verified_strength_import(
        imported,
        activity_key="garmin:42",
        local_start="2026-07-28T10:00:00",
        verified_garmin=Provenance(provider="garmin", reference="activity:42", verified=True),
    )

    assert completed.key == "garmin:42"
    assert completed.strength == imported.workout
    assert completed.provenance.verified is True
