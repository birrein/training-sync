import pytest

from training_sync.domain.planned_workout import planned_workout_from_dict
from training_sync.garmin.planned_workouts import (
    ExerciseResolutionError,
    ExerciseResolutionConflictError,
    ProviderStepLimitError,
    project_planned_workout,
)
from training_sync.garmin.workout_steps import (
    WorkoutStepDecodeError,
    decode_workout_steps,
)
from training_sync.renderers.planned_workout import render_planned_workout


def strength_plan(exercises, *, warmup=None):
    plan = {
        "schema_version": 1,
        "key": "strength-sequence",
        "name": "Strength Sequence",
        "sport": "strength_training",
        "exercises": exercises,
    }
    if warmup is not None:
        plan["warmup"] = warmup
    return plan


def set_with_load(reps, kg, basis="total"):
    return {"reps": reps, "load": {"kind": "mass", "kg": kg, "basis": basis}}


def active_steps(projection):
    return [step for step in projection.steps if step["stepType"]["stepTypeKey"] != "rest"]


def decoder_step(*, rest=False, manual=False, order=1):
    if rest:
        condition = "lap.button" if manual else "time"
        value = None if manual else 75
        unit = None if manual else "seconds"
        description = "Manual rest" if manual else "Rest 75 seconds"
        step_type = "rest"
    else:
        condition = "reps"
        value = 9
        unit = "repetitions"
        description = "Dips; bodyweight; 9 reps"
        step_type = "interval"
    return {
        "type": "ExecutableStepDTO",
        "stepOrder": order,
        "childStepId": None,
        "stepType": {"stepTypeKey": step_type},
        "description": description,
        "endCondition": {"conditionTypeKey": condition},
        "endConditionValue": value,
        "preferredEndConditionUnit": unit,
        "category": "PRESS" if not rest else None,
        "exerciseName": "DIPS" if not rest else None,
        "repetitionCount": 9 if not rest else None,
        "weightValue": None,
        "weightUnit": None,
        "weightBasis": None,
        "loadKind": "bodyweight" if not rest else None,
    }


def grouped_fixture(iterations, *, skip_last_rest=False, nested=False, manual_rest=False):
    children = [decoder_step(order=2), decoder_step(rest=True, manual=manual_rest, order=3)]
    if nested:
        children[0] = {
            "type": "RepeatGroupDTO",
            "stepOrder": 2,
            "childStepId": 201,
            "numberOfIterations": 2,
            "endCondition": {"conditionTypeKey": "iterations"},
            "endConditionValue": 2,
            "skipLastRestStep": False,
            "workoutSteps": [decoder_step(order=4)],
        }
    group = {
        "type": "RepeatGroupDTO",
        "stepOrder": 1,
        "childStepId": 101,
        "numberOfIterations": iterations,
        "endCondition": {"conditionTypeKey": "iterations"},
        "endConditionValue": iterations,
        "skipLastRestStep": skip_last_rest,
        "workoutSteps": children,
    }
    return {
        "workoutSegments": [
            {"segmentOrder": 1, "workoutSteps": [group]}
        ]
    }


@pytest.mark.parametrize("iterations", [2, 3, 4, 5])
def test_decoder_expands_n_iteration_groups_and_retains_final_rest(iterations):
    decoded = decode_workout_steps(grouped_fixture(iterations))

    assert len(decoded.steps) == iterations * 2
    assert [step["stepType"]["stepTypeKey"] for step in decoded.steps] == [
        value
        for _ in range(iterations)
        for value in ("interval", "rest")
    ]
    assert decoded.repeat_groups[0].iterations == iterations
    assert decoded.repeat_groups[0].skip_last_rest_step is False


def test_decoder_expands_historical_skipped_last_rest_without_rewriting_it():
    decoded = decode_workout_steps(grouped_fixture(3, skip_last_rest=True))

    assert [step["stepType"]["stepTypeKey"] for step in decoded.steps] == [
        "interval",
        "rest",
        "interval",
        "rest",
        "interval",
    ]
    assert decoded.repeat_groups[0].skip_last_rest_step is True


def test_decoder_preserves_manual_rest_termination():
    decoded = decode_workout_steps(grouped_fixture(2, manual_rest=True))

    assert decoded.steps[1]["endCondition"]["conditionTypeKey"] == "lap.button"
    assert decoded.steps[1]["endConditionValue"] is None


@pytest.mark.parametrize("iterations", [0, -1, 1.5, True, "2", None])
def test_decoder_rejects_malformed_repeat_counts(iterations):
    with pytest.raises(WorkoutStepDecodeError, match="numberOfIterations"):
        decode_workout_steps(grouped_fixture(iterations))


def test_decoder_rejects_nested_repeat_groups_before_expansion():
    with pytest.raises(WorkoutStepDecodeError, match="nested"):
        decode_workout_steps(grouped_fixture(2, nested=True))


def test_decoder_rejects_expansion_above_the_safety_bound_before_allocation():
    with pytest.raises(WorkoutStepDecodeError, match="expanded workout step limit"):
        decode_workout_steps(grouped_fixture(10001))


def payload_steps(projection):
    return projection.payload["workoutSegments"][0]["workoutSteps"]


def repeat_groups(projection):
    return [step for step in payload_steps(projection) if step.get("type") == "RepeatGroupDTO"]


def test_equal_strength_sets_emit_one_maximal_repeat_group_with_every_rest():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Dip",
                    "sets": [
                        {"reps": 9, "load": {"kind": "bodyweight"}},
                        {"reps": 9, "load": {"kind": "bodyweight"}},
                        {"reps": 9, "load": {"kind": "bodyweight"}},
                    ],
                    "rest_between_sets": {"until": "time", "seconds": 120},
                    "rest_after_exercise": {"until": "time", "seconds": 120},
                }
            ]
        )
    )

    projection = project_planned_workout(plan)
    groups = repeat_groups(projection)

    assert len(groups) == 1
    assert groups[0]["numberOfIterations"] == 3
    assert groups[0]["skipLastRestStep"] is False
    assert [child["stepType"]["stepTypeKey"] for child in groups[0]["workoutSteps"]] == [
        "interval",
        "rest",
    ]
    assert [step["stepType"]["stepTypeKey"] for step in projection.steps] == [
        "interval",
        "rest",
        "interval",
        "rest",
        "interval",
        "rest",
    ]
    assert "Repeat groups: 3 iterations (skipLastRestStep=false)" in projection.preview
    decoded = decode_workout_steps(projection.payload)
    assert [step["stepType"]["stepTypeKey"] for step in decoded.steps] == [
        step["stepType"]["stepTypeKey"] for step in projection.steps
    ]


@pytest.mark.parametrize(
    "second_run_change",
    [
        {"load": {"kind": "mass", "kg": 54, "basis": "total"}},
        {"description": "paused at the top"},
    ],
)
def test_grouping_is_maximal_and_stops_at_load_or_instruction_changes(second_run_change):
    first = set_with_load(10, 53)
    second = {**set_with_load(10, 53), **second_run_change}
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Bench Press",
                    "sets": [first, first, second, second],
                    "rest_between_sets": {"until": "time", "seconds": 75},
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    groups = repeat_groups(project_planned_workout(plan))

    assert [group["numberOfIterations"] for group in groups] == [2, 2]


@pytest.mark.parametrize(
    ("load", "expected_weight", "expected_description"),
    [
        ({"kind": "bodyweight"}, None, "bodyweight"),
        ({"kind": "mass", "kg": 5, "basis": "per_hand"}, 5000, "both sides"),
    ],
)
def test_group_preserves_bodyweight_and_per_hand_load_semantics(
    load, expected_weight, expected_description
):
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Dumbbell Lateral Raise",
                    "sets": [
                        {"reps": 15, "load": load},
                        {"reps": 15, "load": load},
                    ],
                    "rest_between_sets": {"until": "time", "seconds": 75},
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    group = repeat_groups(project_planned_workout(plan))[0]
    child = group["workoutSteps"][0]

    assert child["weightValue"] == expected_weight
    assert expected_description in child["description"]
    if expected_weight is not None:
        assert child["weightBasis"] == "per_hand"


def test_manual_bilbo_stays_flat_while_following_normal_sets_group():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Barbell Bench Press",
                    "sets": [
                        {
                            "termination": {"until": "lap"},
                            "load": {"kind": "mass", "kg": 53, "basis": "total"},
                            "description": "Bilbo set",
                        },
                        {"reps": 12, "load": {"kind": "mass", "kg": 53, "basis": "total"}},
                        {"reps": 12, "load": {"kind": "mass", "kg": 53, "basis": "total"}},
                    ],
                    "rest_between_sets": {"until": "time", "seconds": 75},
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    projection = project_planned_workout(plan)
    groups = repeat_groups(projection)

    assert len(groups) == 1
    assert groups[0]["numberOfIterations"] == 2
    assert payload_steps(projection)[0]["stepType"]["stepTypeKey"] == "interval"
    assert payload_steps(projection)[0]["endCondition"]["conditionTypeKey"] == "lap.button"


def test_explicit_separate_side_rounds_remain_flat_in_garmin_payload():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Dumbbell Bulgarian Split Squat",
                    "sets": [
                        set_with_load(11, 12, "per_hand"),
                        set_with_load(11, 12, "per_hand"),
                    ],
                    "sides": ["left", "right"],
                    "rest_between_sides": {"until": "time", "seconds": 60},
                    "rest_between_sets": {"until": "time", "seconds": 90},
                    "rest_after_exercise": {"until": "time", "seconds": 90},
                }
            ]
        )
    )

    projection = project_planned_workout(plan)

    assert repeat_groups(projection) == []
    assert all(step.get("type") != "RepeatGroupDTO" for step in payload_steps(projection))


def test_missing_final_strength_rest_is_rejected_before_projection():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Face Pull",
                    "sets": [set_with_load(12, 5)],
                    "rest_between_sets": None,
                    "rest_after_exercise": None,
                }
            ]
        )
    )

    with pytest.raises(ValueError, match="rest_after_exercise"):
        project_planned_workout(plan)


def test_missing_inter_set_strength_rest_is_rejected_before_projection():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Face Pull",
                    "sets": [set_with_load(12, 5), set_with_load(12, 5)],
                    "rest_between_sets": None,
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    with pytest.raises(ValueError, match="rest_between_sets"):
        project_planned_workout(plan)


def test_different_final_transition_rest_keeps_equal_sets_separate():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Face Pull",
                    "sets": [set_with_load(12, 5), set_with_load(12, 5)],
                    "rest_between_sets": {"until": "time", "seconds": 75},
                    "rest_after_exercise": {"until": "time", "seconds": 120},
                }
            ]
        )
    )

    projection = project_planned_workout(plan)

    assert repeat_groups(projection) == []
    assert [
        step["endConditionValue"]
        for step in projection.steps
        if step["stepType"]["stepTypeKey"] == "rest"
    ] == [75, 120]


def test_rdl_transition_rest_is_preserved_after_final_set_before_next_exercise():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Romanian Deadlift",
                    "sets": [set_with_load(10, 83), set_with_load(10, 83), set_with_load(10, 83)],
                    "rest_between_sets": {"until": "time", "seconds": 165},
                    "rest_after_exercise": {"until": "time", "seconds": 165},
                },
                {
                    "name": "Barbell Hip Thrust with Bench",
                    "sets": [set_with_load(11, 80), set_with_load(11, 80)],
                    "rest_between_sets": {"until": "time", "seconds": 165},
                    "rest_after_exercise": {"until": "time", "seconds": 165},
                },
            ]
        )
    )

    projection = project_planned_workout(plan)
    steps = projection.steps

    assert [step["stepOrder"] for step in steps] == list(range(1, 11))
    assert [step["stepType"]["stepTypeKey"] for step in steps] == [
        "interval",
        "rest",
        "interval",
        "rest",
        "interval",
        "rest",
        "interval",
        "rest",
        "interval",
        "rest",
    ]
    assert steps[5]["endConditionValue"] == 165
    assert steps[6]["exerciseName"] == "BARBELL_HIP_THRUST_WITH_BENCH"
    assert steps[5]["description"] == "Rest 165 seconds before Barbell Hip Thrust with Bench"


def test_unilateral_sets_are_combined_by_default_and_rest_after_both_sides():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Dumbbell Lateral Raise",
                    "sets": [set_with_load(15, 12.5, "per_hand"), set_with_load(15, 12.5, "per_hand")],
                    "rest_between_sets": {"until": "time", "seconds": 75},
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    projection = project_planned_workout(plan)
    active = active_steps(projection)
    rests = [step for step in projection.steps if step["stepType"]["stepTypeKey"] == "rest"]

    assert len(active) == 2
    assert [step["repetitionCount"] for step in active] == [15, 15]
    assert all("both sides" in step["description"] for step in active)
    assert [step["weightValue"] for step in active] == [12500, 12500]
    assert [step["weightBasis"] for step in active] == ["per_hand", "per_hand"]
    assert [step["endConditionValue"] for step in rests] == [75, 75]


def test_explicit_separate_side_rounds_include_side_and_side_rest():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Dumbbell Bulgarian Split Squat",
                    "sets": [set_with_load(11, 12, "per_hand"), set_with_load(11, 12, "per_hand")],
                    "sides": ["left", "right"],
                    "rest_between_sides": {"until": "time", "seconds": 60},
                    "rest_between_sets": {"until": "time", "seconds": 90},
                    "rest_after_exercise": {"until": "time", "seconds": 90},
                }
            ]
        )
    )

    projection = project_planned_workout(plan)

    assert [step["side"] for step in active_steps(projection)] == ["left", "right", "left", "right"]
    assert [step["endConditionValue"] for step in projection.steps if step["stepType"]["stepTypeKey"] == "rest"] == [
        60,
        90,
        60,
        90,
    ]


def test_missing_final_rest_is_rejected_even_when_warmup_exists():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Squat",
                    "sets": [set_with_load(5, 100)],
                    "rest_between_sets": None,
                    "rest_after_exercise": None,
                }
            ],
            warmup={"until": "lap", "description": "8-10 min"},
        )
    )

    with pytest.raises(ValueError, match="rest_after_exercise"):
        project_planned_workout(plan)


def test_timed_and_manual_lap_sets_preserve_termination_and_load():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Barbell Bench Press",
                    "sets": [
                        {
                            "termination": {"until": "time", "seconds": 48.5},
                            "load": {"kind": "mass", "kg": 50, "basis": "total"},
                            "description": "Bilbo set",
                        },
                        {
                            "termination": {"until": "lap"},
                            "load": {"kind": "mass", "kg": 45, "basis": "total"},
                            "description": "Bilbo set",
                        },
                    ],
                    "rest_between_sets": {"until": "time", "seconds": 75},
                    "rest_after_exercise": {"until": "lap"},
                }
            ]
        )
    )

    active = active_steps(project_planned_workout(plan))

    assert active[0]["endCondition"]["conditionTypeKey"] == "time"
    assert active[0]["endConditionValue"] == 48.5
    assert active[0]["weightValue"] == 50000
    assert active[1]["endCondition"]["conditionTypeKey"] == "lap.button"
    assert active[1]["endConditionValue"] is None
    assert active[1]["weightValue"] == 45000


def test_explicit_substitute_exposes_original_and_catalog_identity():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Dragon Flag",
                    "garmin_name": "Reverse Crunch on a Bench",
                    "sets": [{"reps": 8, "load": {"kind": "bodyweight"}}],
                    "rest_between_sets": {"until": "time", "seconds": 75},
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    projection = project_planned_workout(plan)
    step = active_steps(projection)[0]

    assert step["exerciseName"] == "REVERSE_CRUNCH_ON_A_BENCH"
    assert step["category"] == "CRUNCH"
    assert step["originalExerciseName"] == "Dragon Flag"
    assert "Dragon Flag" in step["description"]
    assert "Reverse Crunch on a Bench" in step["description"]


def test_unresolved_exercise_is_rejected_instead_of_projecting_unknown():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Exercise That Garmin Does Not Have",
                    "sets": [{"reps": 8, "load": {"kind": "bodyweight"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    with pytest.raises(ExerciseResolutionError, match="Exercise That Garmin"):
        project_planned_workout(plan)


def test_repeated_endurance_blocks_are_flattened_and_keep_power_target_bounds():
    plan = planned_workout_from_dict(
        {
            "schema_version": 1,
            "key": "bike-intervals",
            "name": "Indoor Bike Intervals",
            "sport": "cycling",
            "context": "indoor",
            "blocks": [
                {"role": "warmup", "steps": [{"termination": {"until": "time", "seconds": 600}}]},
                {
                    "role": "work",
                    "repeat": 2,
                    "steps": [
                        {
                            "termination": {"until": "time", "seconds": 180},
                            "target": {"kind": "power", "watts": {"min": 200, "max": 220}},
                        },
                        {"role": "recovery", "termination": {"until": "time", "seconds": 120}},
                    ],
                },
                {"role": "cooldown", "steps": [{"termination": {"until": "time", "seconds": 300}}]},
            ],
        }
    )

    projection = project_planned_workout(plan)
    assert [step["stepOrder"] for step in projection.steps] == list(range(1, 7))
    assert [step["stepType"]["stepTypeKey"] for step in projection.steps] == [
        "warmup",
        "interval",
        "recovery",
        "interval",
        "recovery",
        "cooldown",
    ]
    assert [(step["targetValueOne"], step["targetValueTwo"], step["targetValueUnit"]) for step in projection.steps if step.get("targetValueUnit")] == [
        (200, 220, "watts"),
        (200, 220, "watts"),
    ]


def test_preview_renders_the_same_projected_step_sequence_and_load_basis():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Dumbbell Lateral Raise",
                    "sets": [set_with_load(15, 12.5, "per_hand")],
                    "rest_between_sets": None,
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )
    projection = project_planned_workout(plan)
    preview = render_planned_workout(plan)

    assert preview == projection.preview
    assert "Dumbbell Lateral Raise" in preview
    assert "12.5 kg per hand" in preview
    assert "both sides" in preview


def test_existing_mapping_precedes_conflicting_catalog_entry():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Face Pull",
                    "sets": [{"reps": 12, "load": {"kind": "bodyweight"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    projection = project_planned_workout(
        plan,
        garmin_dict={
            "FACE PULL": {"category": "SUSPENSION", "name": "FACE_PULL"}
        },
    )

    assert projection.steps[0]["category"] == "ROW"
    assert projection.steps[0]["exerciseName"] == "FACE_PULL"


def test_explicit_garmin_name_precedes_existing_generic_mapping():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Face Pull",
                    "garmin_name": "Face Pull",
                    "sets": [{"reps": 12, "load": {"kind": "bodyweight"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    projection = project_planned_workout(
        plan,
        garmin_dict={
            "FACE PULL": {"category": "SUSPENSION", "name": "FACE_PULL"}
        },
    )

    assert projection.steps[0]["category"] == "SUSPENSION"
    assert projection.steps[0]["exerciseName"] == "FACE_PULL"


def test_ambiguous_normalized_catalog_mapping_is_rejected():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Mystery Move",
                    "sets": [{"reps": 8, "load": {"kind": "bodyweight"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    with pytest.raises(ExerciseResolutionConflictError, match="conflicting"):
        project_planned_workout(
            plan,
            garmin_dict={
                "MYSTERY_MOVE": {"category": "A", "name": "MOVE_A"},
                "Mystery Move": {"category": "B", "name": "MOVE_B"},
            },
        )


def test_provider_step_limit_fails_without_truncating_sequence():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Squat",
                    "sets": [{"reps": 5, "load": {"kind": "bodyweight"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": {"until": "time", "seconds": 75},
                }
            ]
        )
    )

    with pytest.raises(ProviderStepLimitError, match="truncated"):
        project_planned_workout(plan, max_steps=0)


def test_running_power_preserves_range_and_time_termination():
    plan = planned_workout_from_dict(
        {
            "schema_version": 1,
            "key": "running-power",
            "name": "Running Power",
            "sport": "running",
            "blocks": [
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
                }
            ],
        }
    )

    projection = project_planned_workout(plan)

    assert len(projection.steps) == 10
    assert all(step["endCondition"]["conditionTypeKey"] == "time" for step in projection.steps)
    assert [(step["targetValueOne"], step["targetValueTwo"], step["targetValueUnit"]) for step in projection.steps[::2]] == [(250, 270, "watts")] * 5


def test_running_distance_keeps_pace_bounds_in_explicit_seconds_per_km():
    plan = planned_workout_from_dict(
        {
            "schema_version": 1,
            "key": "running-distance",
            "name": "400m Repeats",
            "sport": "running",
            "blocks": [
                {
                    "role": "work",
                    "repeat": 2,
                    "steps": [
                        {
                            "termination": {"until": "distance", "meters": 400},
                            "target": {"kind": "pace", "seconds_per_km": {"min": 240, "max": 270}},
                        },
                        {"role": "recovery", "termination": {"until": "time", "seconds": 90}},
                    ],
                }
            ],
        }
    )

    work = project_planned_workout(plan).steps[0]
    assert work["endCondition"]["conditionTypeKey"] == "distance"
    assert work["endConditionValue"] == 400
    assert (work["targetValueOne"], work["targetValueTwo"], work["targetValueUnit"]) == (240, 270, "seconds_per_km")


def test_cycling_cadence_target_is_preserved_and_running_cadence_is_rejected():
    cycling = planned_workout_from_dict(
        {
            "schema_version": 1,
            "key": "cycling-cadence",
            "name": "Cadence",
            "sport": "cycling",
            "blocks": [
                {
                    "role": "work",
                    "steps": [
                        {
                            "termination": {"until": "time", "seconds": 60},
                            "target": {"kind": "cadence", "rpm": {"min": 85, "max": 95}},
                        }
                    ],
                }
            ],
        }
    )
    step = project_planned_workout(cycling).steps[0]
    assert (step["targetValueOne"], step["targetValueTwo"], step["targetValueUnit"]) == (85, 95, "rpm")

    with pytest.raises(ValueError, match="cadence"):
        planned_workout_from_dict(
            {
                "schema_version": 1,
                "key": "running-cadence",
                "name": "Unsupported Cadence",
                "sport": "running",
                "blocks": [
                    {
                        "role": "work",
                        "steps": [
                            {
                                "termination": {"until": "time", "seconds": 60},
                                "target": {"kind": "cadence", "rpm": 90},
                            }
                        ],
                    }
                ],
            }
        )
