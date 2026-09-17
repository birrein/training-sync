import math

import pytest

from training_sync.domain.planned_workout import (
    PlannedWorkoutValidationError,
    planned_workout_from_dict,
)


def strength_plan(**overrides):
    plan = {
        "schema_version": 1,
        "key": "lower-body-2-2026-09-13",
        "name": "Lower Body 2",
        "sport": "strength_training",
        "exercises": [
            {
                "name": "Romanian Deadlift",
                "sets": [
                    {"reps": 10, "load": {"kind": "mass", "kg": 83, "basis": "total"}},
                    {"reps": 8, "load": {"kind": "mass", "kg": 85, "basis": "total"}},
                ],
                "rest_between_sets": {"until": "time", "seconds": 165},
                "rest_after_exercise": {"until": "time", "seconds": 165},
            }
        ],
    }
    plan.update(overrides)
    return plan


def interval_plan(**overrides):
    plan = {
        "schema_version": 1,
        "key": "running-power-2026-09-13",
        "name": "Running Power",
        "sport": "running",
        "blocks": [
            {
                "role": "warmup",
                "steps": [{"termination": {"until": "time", "seconds": 600}}],
            },
            {
                "role": "work",
                "repeat": 5,
                "steps": [
                    {
                        "termination": {"until": "time", "seconds": 180},
                        "target": {"kind": "power", "watts": {"min": 250, "max": 270}},
                    },
                    {"role": "recovery", "termination": {"until": "time", "seconds": 120}},
                ],
            },
            {
                "role": "cooldown",
                "steps": [{"termination": {"until": "time", "seconds": 300}}],
            },
        ],
    }
    plan.update(overrides)
    return plan


def test_versioned_input_keeps_provenance_out_of_execution_content():
    with_provenance = strength_plan(
        provenance={"source": "fitbod-screenshot", "captured_at": "2026-09-12T20:00:00-04:00"}
    )

    parsed = planned_workout_from_dict(with_provenance)
    equivalent = planned_workout_from_dict(strength_plan())

    assert parsed.schema_version == 1
    assert parsed.provenance == with_provenance["provenance"]
    assert parsed.execution_dict() == equivalent.execution_dict()
    assert parsed.execution_hash() == equivalent.execution_hash()


def test_strength_preserves_unequal_sets_and_load_basis():
    parsed = planned_workout_from_dict(strength_plan())

    sets = parsed.exercises[0].sets
    assert [(item.reps, item.load.kg, item.load.basis) for item in sets] == [
        (10, 83.0, "total"),
        (8, 85.0, "total"),
    ]


@pytest.mark.parametrize(
    ("load", "kind", "kg", "basis"),
    [
        ({"kind": "bodyweight"}, "bodyweight", None, None),
        ({"kind": "mass", "kg": 12.5, "basis": "per_hand"}, "mass", 12.5, "per_hand"),
    ],
)
def test_strength_loads_preserve_bodyweight_and_per_hand_semantics(load, kind, kg, basis):
    parsed = planned_workout_from_dict(
        strength_plan(
            exercises=[
                {
                    "name": "Lateral Raise",
                    "sets": [{"reps": 15, "load": load}],
                    "rest_between_sets": {"until": "time", "seconds": 75},
                    "rest_after_exercise": None,
                }
            ]
        )
    )

    observed = parsed.exercises[0].sets[0].load
    assert (observed.kind, observed.kg, observed.basis) == (kind, kg, basis)


def test_strength_supports_timed_and_manual_lap_sets_without_inventing_reps():
    parsed = planned_workout_from_dict(
        strength_plan(
            exercises=[
                {
                    "name": "Bilbo Press",
                    "sets": [
                        {
                            "termination": {"until": "time", "seconds": 48.5},
                            "load": {"kind": "mass", "kg": 50, "basis": "total"},
                        },
                        {
                            "termination": {"until": "lap"},
                            "load": {"kind": "mass", "kg": 45, "basis": "total"},
                        },
                    ],
                    "rest_between_sets": None,
                    "rest_after_exercise": {"until": "lap"},
                }
            ]
        )
    )

    assert parsed.exercises[0].sets[0].reps is None
    assert parsed.exercises[0].sets[0].termination.until == "time"
    assert parsed.exercises[0].sets[0].termination.value == 48.5
    assert parsed.exercises[0].sets[1].termination.until == "lap"
    assert parsed.exercises[0].sets[1].reps is None
    assert parsed.exercises[0].rest_after_exercise.until == "lap"


def test_lap_warmup_and_explicit_null_final_rest_are_preserved():
    parsed = planned_workout_from_dict(
        strength_plan(
            warmup={"until": "lap", "description": "8-10 min"},
            exercises=[
                {
                    "name": "Squat",
                    "sets": [{"reps": 5, "load": {"kind": "mass", "kg": 100, "basis": "total"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": None,
                }
            ],
        )
    )

    assert parsed.warmup.termination.until == "lap"
    assert parsed.warmup.description == "8-10 min"
    assert parsed.exercises[0].rest_after_exercise is None


def test_endurance_preserves_time_distance_targets_and_repeated_blocks():
    parsed = planned_workout_from_dict(
        interval_plan(
            sport="cycling",
            context="indoor",
            blocks=[
                {"role": "warmup", "steps": [{"termination": {"until": "time", "seconds": 600}}]},
                {
                    "role": "work",
                    "repeat": 3,
                    "steps": [
                        {
                            "termination": {"until": "distance", "meters": 1000},
                            "target": {"kind": "power", "watts": {"min": 200, "max": 220}},
                        },
                        {
                            "role": "recovery",
                            "termination": {"until": "time", "seconds": 120},
                            "target": {"kind": "cadence", "rpm": {"min": 85, "max": 95}},
                        },
                    ],
                },
            ],
        )
    )

    assert parsed.context == "indoor"
    assert parsed.blocks[1].repeat == 3
    assert parsed.blocks[1].steps[0].termination.until == "distance"
    assert parsed.blocks[1].steps[0].termination.value == 1000
    assert parsed.blocks[1].steps[0].termination.unit == "meters"
    assert parsed.blocks[1].steps[0].target.lower == 200
    assert parsed.blocks[1].steps[0].target.upper == 220
    assert parsed.blocks[1].steps[1].target.unit == "rpm"


def test_running_power_target_is_distinct_from_time_termination():
    parsed = planned_workout_from_dict(interval_plan())

    work = parsed.blocks[1].steps[0]
    assert work.termination.until == "time"
    assert work.termination.unit == "seconds"
    assert work.target.kind == "power"
    assert work.target.unit == "watts"
    assert (work.target.lower, work.target.upper) == (250, 270)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda plan: plan.update({"unknown": True}), "unknown field 'unknown'"),
        (lambda plan: plan.update({"schema_version": 2}), "schema_version"),
        (
            lambda plan: plan["exercises"][0]["sets"][0].update({"reps": 0}),
            "reps",
        ),
        (
            lambda plan: plan["exercises"][0]["sets"][0]["load"].update({"kg": math.inf}),
            "kg",
        ),
        (
            lambda plan: plan["exercises"][0]["sets"][0].update(
                {"reps": 10, "termination": {"until": "time", "seconds": 30}}
            ),
            "termination",
        ),
    ],
)
def test_invalid_planned_input_fails_with_field_specific_errors(mutator, message):
    plan = strength_plan()
    mutator(plan)

    with pytest.raises(PlannedWorkoutValidationError, match=message):
        planned_workout_from_dict(plan)


def test_unresolved_duration_range_is_rejected_instead_of_choosing_a_midpoint():
    plan = interval_plan(
        blocks=[
            {
                "role": "work",
                "steps": [
                    {"termination": {"until": "time", "seconds": {"min": 30, "max": 45}}}
                ],
            }
        ]
    )

    with pytest.raises(PlannedWorkoutValidationError, match="seconds"):
        planned_workout_from_dict(plan)


def test_boolean_is_not_accepted_as_numeric_value():
    plan = strength_plan(
        exercises=[
            {
                "name": "Squat",
                "sets": [{"reps": True, "load": {"kind": "bodyweight"}}],
            }
        ]
    )

    with pytest.raises(PlannedWorkoutValidationError, match="reps"):
        planned_workout_from_dict(plan)


def test_malformed_plan_date_is_rejected_without_becoming_schedule_date():
    with pytest.raises(PlannedWorkoutValidationError, match="date"):
        planned_workout_from_dict(strength_plan(date="2026-13-99"))


def test_omitted_or_one_repeat_keeps_the_previous_physical_set_and_hash():
    explicit = strength_plan(
        exercises=[
            {
                "name": "Squat",
                "sets": [
                    {"reps": 5, "load": {"kind": "mass", "kg": 100, "basis": "total"}}
                ],
                "rest_between_sets": {"until": "time", "seconds": 120},
                "rest_after_exercise": {"until": "time", "seconds": 120},
            }
        ]
    )
    compact_one = strength_plan(
        exercises=[
            {
                "name": "Squat",
                "sets": [
                    {
                        "repeat": 1,
                        "reps": 5,
                        "load": {"kind": "mass", "kg": 100, "basis": "total"},
                    }
                ],
                "rest_between_sets": {"until": "time", "seconds": 120},
                "rest_after_exercise": {"until": "time", "seconds": 120},
            }
        ]
    )

    parsed_explicit = planned_workout_from_dict(explicit)
    parsed_compact = planned_workout_from_dict(compact_one)

    assert len(parsed_compact.exercises[0].sets) == 1
    assert parsed_compact.execution_dict() == parsed_explicit.execution_dict()
    assert parsed_compact.execution_hash() == parsed_explicit.execution_hash()


def test_positive_repeat_expands_consecutive_whole_sets_without_multiplying_reps_or_load():
    parsed = planned_workout_from_dict(
        strength_plan(
            exercises=[
                {
                    "name": "Bench Press",
                    "sets": [
                        {"reps": 8, "load": {"kind": "mass", "kg": 53, "basis": "total"}},
                        {
                            "repeat": 3,
                            "reps": 10,
                            "load": {"kind": "mass", "kg": 60, "basis": "total"},
                        },
                    ],
                    "rest_between_sets": {"until": "time", "seconds": 90},
                    "rest_after_exercise": {"until": "time", "seconds": 90},
                }
            ]
        )
    )

    assert [item.reps for item in parsed.exercises[0].sets] == [8, 10, 10, 10]
    assert [item.load.kg for item in parsed.exercises[0].sets] == [53, 60, 60, 60]


def test_mixed_explicit_and_repeated_entries_preserve_input_order():
    parsed = planned_workout_from_dict(
        strength_plan(
            exercises=[
                {
                    "name": "Row",
                    "sets": [
                        {"reps": 5, "load": {"kind": "mass", "kg": 40, "basis": "total"}},
                        {
                            "repeat": 2,
                            "reps": 12,
                            "load": {"kind": "mass", "kg": 45, "basis": "total"},
                        },
                        {"reps": 8, "load": {"kind": "mass", "kg": 50, "basis": "total"}},
                    ],
                    "rest_between_sets": {"until": "time", "seconds": 75},
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    assert [item.reps for item in parsed.exercises[0].sets] == [5, 12, 12, 8]
    assert [item.load.kg for item in parsed.exercises[0].sets] == [40, 45, 45, 50]


@pytest.mark.parametrize(
    "termination",
    [
        {"until": "time", "seconds": 48.5},
        {"until": "lap"},
    ],
)
def test_repeated_time_and_lap_entries_retain_termination_without_inventing_reps(termination):
    parsed = planned_workout_from_dict(
        strength_plan(
            exercises=[
                {
                    "name": "Bilbo Press",
                    "sets": [
                        {
                            "repeat": 2,
                            "termination": termination,
                            "load": {"kind": "mass", "kg": 50, "basis": "total"},
                        }
                    ],
                    "rest_between_sets": {"until": "time", "seconds": 60},
                    "rest_after_exercise": {"until": "time", "seconds": 60},
                }
            ]
        )
    )

    sets = parsed.exercises[0].sets
    assert len(sets) == 2
    assert all(item.reps is None for item in sets)
    assert [item.termination.to_dict() for item in sets] == [
        {"until": "time", "seconds": 48.5}
        if termination["until"] == "time"
        else {"until": "lap"},
        {"until": "time", "seconds": 48.5}
        if termination["until"] == "time"
        else {"until": "lap"},
    ]


def test_repeated_explicit_side_rounds_keep_complete_round_semantics():
    parsed = planned_workout_from_dict(
        strength_plan(
            exercises=[
                {
                    "name": "Bulgarian Split Squat",
                    "sets": [
                        {
                            "repeat": 2,
                            "reps": 11,
                            "load": {"kind": "mass", "kg": 12, "basis": "per_hand"},
                        }
                    ],
                    "sides": ["left", "right"],
                    "rest_between_sides": {"until": "time", "seconds": 60},
                    "rest_between_sets": {"until": "time", "seconds": 90},
                    "rest_after_exercise": {"until": "time", "seconds": 90},
                }
            ]
        )
    )

    exercise = parsed.exercises[0]
    assert len(exercise.sets) == 2
    assert exercise.sides == ("left", "right")
    assert exercise.rest_between_sides.to_dict() == {"until": "time", "seconds": 60}


@pytest.mark.parametrize("repeat", [0, -1, 1.5, True, "2", None])
def test_invalid_strength_repeat_is_rejected_with_a_field_specific_error(repeat):
    with pytest.raises(PlannedWorkoutValidationError, match="repeat"):
        planned_workout_from_dict(
            strength_plan(
                exercises=[
                    {
                        "name": "Squat",
                        "sets": [
                            {
                                "repeat": repeat,
                                "reps": 5,
                                "load": {"kind": "bodyweight"},
                            }
                        ],
                        "rest_between_sets": {"until": "time", "seconds": 90},
                        "rest_after_exercise": {"until": "time", "seconds": 90},
                    }
                ]
            )
        )


def test_aggregate_repeat_expansion_is_bounded_before_allocation():
    with pytest.raises(PlannedWorkoutValidationError, match="expanded strength set limit"):
        planned_workout_from_dict(
            strength_plan(
                exercises=[
                    {
                        "name": "Squat",
                        "sets": [
                            {
                                "repeat": 1001,
                                "reps": 5,
                                "load": {"kind": "bodyweight"},
                            }
                        ],
                        "rest_between_sets": {"until": "time", "seconds": 90},
                        "rest_after_exercise": {"until": "time", "seconds": 90},
                    }
                ]
            )
        )
