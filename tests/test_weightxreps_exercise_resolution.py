import pytest

from training_sync.weightxreps.exercise_mapping import load_exercise_mappings
from training_sync.weightxreps.exercise_resolution import (
    ExerciseResolutionRequired,
    resolve_exercise_ids,
)


def test_load_exercise_mappings_reads_aliases_from_toml(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"
    mapping_path.write_text(
        """[[exercises]]
weightxreps_name = "Barbell Hip Thrust"
weightxreps_id = 157721
aliases = [
  "Hip Thrust",
  "Barbell Hip Thrust with Bench",
]
""",
        encoding="utf-8",
    )

    mappings = load_exercise_mappings(mapping_path)

    assert mappings[0].weightxreps_name == "Barbell Hip Thrust"
    assert mappings[0].weightxreps_id == 157721
    assert mappings[0].aliases == [
        "Hip Thrust",
        "Barbell Hip Thrust with Bench",
    ]


def test_resolve_exercise_ids_uses_local_alias_before_remote_names(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"
    mapping_path.write_text(
        """[[exercises]]
weightxreps_name = "Barbell Hip Thrust"
weightxreps_id = 157721
aliases = ["Hip Thrust"]
""",
        encoding="utf-8",
    )
    mappings = load_exercise_mappings(mapping_path)

    resolved = resolve_exercise_ids(
        date="2026-06-20",
        exercise_names=["Hip Thrust"],
        local_mappings=mappings,
        remote_exercise_ids={"Hip Thrust": 999999},
    )

    assert resolved == {"Hip Thrust": 157721}


def test_resolve_exercise_ids_raises_structured_payload_for_unknown_name():
    with pytest.raises(ExerciseResolutionRequired) as exc:
        resolve_exercise_ids(
            date="2026-06-20",
            exercise_names=["Barbell Hip Thrust with Bench"],
            local_mappings=[],
            remote_exercise_ids={"Barbell Hip Thrust": 157721},
        )

    assert exc.value.payload() == {
        "status": "exercise_resolution_required",
        "date": "2026-06-20",
        "unresolved": [
            {
                "incoming_exercise": "Barbell Hip Thrust with Bench",
                "normalized_name": "barbell hip thrust with bench",
                "reason": "no_local_mapping",
                "candidates": [
                    {
                        "weightxreps_id": 157721,
                        "weightxreps_name": "Barbell Hip Thrust",
                        "match_reason": "similar_name",
                    }
                ],
                "allowed_actions": [
                    "map_to_existing",
                    "create_new",
                    "skip_workout",
                ],
            }
        ],
        "suggested_agent_question": (
            "How should I resolve 'Barbell Hip Thrust with Bench': map it to an "
            "existing candidate, create it as a new Weight x Reps exercise, or skip this sync?"
        ),
    }
