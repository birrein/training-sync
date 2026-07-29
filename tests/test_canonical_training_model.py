from datetime import datetime

from training_sync.domain.training import (
    CompletedActivity,
    EffortObservation,
    EffortScope,
    Load,
    LoadKind,
    Provenance,
    SourceArtifact,
    StrengthExercise,
    StrengthSet,
    StrengthWorkout,
)


def test_completed_activity_retains_provenance_and_opaque_source_artifact():
    provenance = Provenance(provider="garmin", reference="activity:42", verified=True)
    artifact = SourceArtifact(kind="fit", reference="garmin://activities/42/file")
    activity = CompletedActivity(
        key="garmin:42",
        title="Morning Ride",
        activity_type="cycling",
        local_start=datetime(2026, 7, 28, 7, 30),
        elapsed_duration_s=3600,
        active_duration_s=3450,
        provenance=provenance,
        source_artifacts=(artifact,),
        objective_summary={"distance_m": 25000.0},
    )

    assert activity.provenance.verified is True
    assert activity.source_artifacts == (artifact,)
    assert "telemetry" not in activity.__dict__


def test_strength_preserves_order_roles_and_mixed_loads():
    workout = StrengthWorkout(
        exercises=(
            StrengthExercise(
                key="dip",
                name="Dip",
                order=0,
                sets=(StrengthSet(order=0, role="active", reps=8, load=Load.bodyweight()),),
            ),
            StrengthExercise(
                key="chin_up",
                name="Chin Up",
                order=1,
                sets=(
                    StrengthSet(
                        order=0,
                        role="warmup",
                        reps=5,
                        load=Load(kind=LoadKind.ASSISTANCE, value=18, unit="kg"),
                    ),
                    StrengthSet(order=1, role="primer", reps=3, load=Load.none()),
                ),
            ),
        )
    )

    assert [exercise.key for exercise in workout.exercises] == ["dip", "chin_up"]
    assert workout.exercises[0].sets[0].load.kind is LoadKind.BODYWEIGHT
    assert workout.exercises[1].sets[0].load.kind is LoadKind.ASSISTANCE
    assert workout.exercises[1].sets[1].load.kind is LoadKind.NONE


def test_effort_observations_keep_their_original_scope():
    source = Provenance(provider="vault", reference="daily/2026-07-28")
    observations = (
        EffortObservation(metric="rir", value=1, scope=EffortScope.EXERCISE, provenance=source, exercise_key="chin_up"),
        EffortObservation(metric="rpe", value=8, scope=EffortScope.SESSION, provenance=source),
        EffortObservation(metric="rpe", value=9, scope=EffortScope.SET, provenance=source, exercise_key="dip", set_order=0),
    )

    assert [item.scope for item in observations] == [EffortScope.EXERCISE, EffortScope.SESSION, EffortScope.SET]
    assert observations[0].set_order is None
    assert observations[1].exercise_key is None
