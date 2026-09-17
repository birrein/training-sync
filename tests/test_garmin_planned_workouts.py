import json
from pathlib import Path

import pytest

from training_sync.domain.planned_workout import planned_workout_from_dict
from training_sync.garmin.planned_workouts import (
    ExerciseResolutionError,
    ExerciseResolutionConflictError,
    ProviderStepLimitError,
    project_planned_workout,
)
from training_sync.renderers.planned_workout import render_planned_workout


FIXTURES = Path(__file__).parent / "fixtures" / "garmin"


def garmin_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


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
                    "rest_after_exercise": None,
                },
            ]
        )
    )

    projection = project_planned_workout(plan)
    steps = projection.steps

    assert [step["stepOrder"] for step in steps] == list(range(1, 10))
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
    assert [step["endConditionValue"] for step in active] == [15, 15]
    assert all(step["endCondition"]["conditionTypeKey"] == "reps" for step in active)
    assert all("both sides" in step["description"] for step in active)
    assert [step["weightValue"] for step in active] == [12.5, 12.5]
    assert all(step["weightUnit"]["unitKey"] == "kilogram" for step in active)
    assert all("12.5 kg per hand" in step["description"] for step in active)
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

    assert [
        "left side" in step["description"]
        for step in active_steps(projection)
    ] == [True, False, True, False]
    assert [
        "right side" in step["description"]
        for step in active_steps(projection)
    ] == [False, True, False, True]
    assert all("side" not in step for step in active_steps(projection))
    assert [step["endConditionValue"] for step in projection.steps if step["stepType"]["stepTypeKey"] == "rest"] == [
        60,
        90,
        60,
        90,
    ]


def test_final_explicit_null_rest_omits_only_terminal_rest():
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

    projection = project_planned_workout(plan)

    assert projection.steps[0]["stepType"]["stepTypeKey"] == "warmup"
    assert projection.steps[0]["endCondition"]["conditionTypeKey"] == "lap.button"
    assert projection.steps[-1]["stepType"]["stepTypeKey"] == "interval"
    assert all(step["stepType"]["stepTypeKey"] != "rest" for step in projection.steps)


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
                    "rest_between_sets": None,
                    "rest_after_exercise": None,
                }
            ]
        )
    )

    active = active_steps(project_planned_workout(plan))

    assert active[0]["endCondition"]["conditionTypeKey"] == "time"
    assert active[0]["endConditionValue"] == 48.5
    assert active[0]["weightValue"] == 50
    assert active[0]["weightUnit"]["unitKey"] == "kilogram"
    assert active[0]["preferredEndConditionUnit"] is None
    assert active[1]["endCondition"]["conditionTypeKey"] == "lap.button"
    assert active[1]["endConditionValue"] is None
    assert active[1]["weightValue"] == 45
    assert active[1]["weightUnit"]["unitKey"] == "kilogram"


def test_explicit_substitute_exposes_original_and_catalog_identity():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Dragon Flag",
                    "garmin_name": "Reverse Crunch on a Bench",
                    "sets": [{"reps": 8, "load": {"kind": "bodyweight"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": None,
                }
            ]
        )
    )

    projection = project_planned_workout(plan)
    step = active_steps(projection)[0]

    assert step["exerciseName"] == "REVERSE_CRUNCH_ON_A_BENCH"
    assert step["category"] == "CRUNCH"
    assert "originalExerciseName" not in step
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
                    "rest_after_exercise": None,
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
                    "rest_after_exercise": None,
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
                    "rest_after_exercise": None,
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
                    "rest_after_exercise": None,
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
                    "rest_after_exercise": None,
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
                    "rest_after_exercise": None,
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


def test_strength_payload_matches_accepted_provider_fixture():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Squat",
                    "sets": [{"reps": 8, "load": {"kind": "mass", "kg": 50, "basis": "total"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": None,
                }
            ]
        )
    )
    expected = garmin_fixture("strength-payload-accepted.json")
    projection = project_planned_workout(plan)
    step = active_steps(projection)[0]

    assert projection.payload["sportType"] == expected["sportType"]
    assert step["endCondition"]["conditionTypeKey"] == expected["weightedStep"]["endCondition"]
    assert step["endConditionValue"] == expected["weightedStep"]["endConditionValue"]
    assert step["preferredEndConditionUnit"] == expected["weightedStep"]["preferredEndConditionUnit"]
    assert step["weightValue"] == expected["weightedStep"]["weightValue"]
    assert step["weightUnit"] == expected["weightedStep"]["weightUnit"]


def test_strength_payload_does_not_use_rejected_wire_representation_or_adapter_fields():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Squat",
                    "sets": [{"reps": 8, "load": {"kind": "mass", "kg": 50, "basis": "total"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": None,
                }
            ]
        )
    )
    rejected = garmin_fixture("strength-payload-rejected.json")
    projection = project_planned_workout(plan)
    step = active_steps(projection)[0]

    assert {
        key: step.get(key)
        for key in rejected["weightedStep"]
    } != rejected["weightedStep"]
    for field in rejected["unsupportedFields"]:
        assert field not in step


def test_dragon_flag_uses_catalog_substitute_and_preserves_instruction_in_description():
    plan = planned_workout_from_dict(
        strength_plan(
            [
                {
                    "name": "Dragon Flag",
                    "garmin_name": "Reverse Crunch on a Bench",
                    "sets": [{"reps": 8, "load": {"kind": "bodyweight"}}],
                    "rest_between_sets": None,
                    "rest_after_exercise": None,
                }
            ]
        )
    )
    expected = garmin_fixture("strength-payload-accepted.json")["dragonFlagStep"]
    step = active_steps(project_planned_workout(plan))[0]

    assert step["category"] == expected["category"]
    assert step["exerciseName"] == expected["exerciseName"]
    assert step["endCondition"]["conditionTypeKey"] == expected["endCondition"]
    assert step["endConditionValue"] == expected["endConditionValue"]
    assert step["preferredEndConditionUnit"] is None
    assert step["weightValue"] is None
    assert step["weightUnit"] is None
    assert "originalExerciseName" not in step
    assert all(fragment in step["description"] for fragment in expected["descriptionIncludes"])
