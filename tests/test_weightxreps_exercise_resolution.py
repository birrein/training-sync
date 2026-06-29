import pytest

from training_sync.weightxreps.exercise_mapping import (
    DuplicateExerciseAliasError,
    ExerciseMapping,
    load_exercise_mappings,
)
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
create_if_missing = true
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
    assert mappings[0].create_if_missing is True
    assert mappings[0].aliases == [
        "Hip Thrust",
        "Barbell Hip Thrust with Bench",
    ]


def test_missing_exercise_mapping_file_loads_empty_list(tmp_path):
    assert load_exercise_mappings(tmp_path / "missing.toml") == []


def test_duplicate_alias_fails_with_both_targets(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"
    mapping_path.write_text(
        """[[exercises]]
weightxreps_name = "Barbell Hip Thrust"
weightxreps_id = 157721
aliases = ["Hip Thrust"]

[[exercises]]
weightxreps_name = "Hip Thrust Machine"
weightxreps_id = 157700
aliases = ["Hip Thrust"]
""",
        encoding="utf-8",
    )

    with pytest.raises(DuplicateExerciseAliasError) as exc:
        load_exercise_mappings(mapping_path)

    assert exc.value.alias == "hip thrust"
    assert exc.value.targets == ["Barbell Hip Thrust", "Hip Thrust Machine"]


def test_duplicate_canonical_name_fails_with_both_targets(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"
    mapping_path.write_text(
        """[[exercises]]
weightxreps_name = "Hip Thrust"
weightxreps_id = 1

[[exercises]]
weightxreps_name = "Hip Thrust"
weightxreps_id = 2
""",
        encoding="utf-8",
    )

    with pytest.raises(DuplicateExerciseAliasError) as exc:
        load_exercise_mappings(mapping_path)

    assert exc.value.alias == "hip thrust"
    assert exc.value.targets == ["Hip Thrust (id=1)", "Hip Thrust (id=2)"]


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
        remote_exercise_ids={"Barbell Hip Thrust": 157721, "Hip Thrust": 999999},
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
        "catalog_source": "unknown",
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


def test_resolution_payload_includes_catalog_source():
    with pytest.raises(ExerciseResolutionRequired) as exc:
        resolve_exercise_ids(
            date="2026-06-20",
            exercise_names=["Unknown Lift"],
            local_mappings=[],
            remote_exercise_ids={},
            catalog_source="partial_jeditor",
        )

    assert exc.value.payload()["catalog_source"] == "partial_jeditor"


def test_mapped_id_resolves_under_partial_jeditor_when_remote_ids_are_empty():
    mappings = [
        ExerciseMapping(
            weightxreps_name="Barbell Hip Thrust",
            weightxreps_id=157721,
            aliases=["Hip Thrust"],
        )
    ]

    resolved = resolve_exercise_ids(
        date="2026-06-20",
        exercise_names=["Hip Thrust"],
        local_mappings=mappings,
        remote_exercise_ids={},
        catalog_source="partial_jeditor",
    )

    assert resolved == {"Hip Thrust": 157721}


def test_mapped_id_missing_from_full_remote_catalog_requires_refresh():
    mappings = [
        ExerciseMapping(
            weightxreps_name="Barbell Hip Thrust",
            weightxreps_id=157721,
            aliases=["Hip Thrust"],
        )
    ]

    with pytest.raises(ExerciseResolutionRequired) as exc:
        resolve_exercise_ids(
            date="2026-06-20",
            exercise_names=["Hip Thrust"],
            local_mappings=mappings,
            remote_exercise_ids={"Hip Thrust Machine": 157700},
            catalog_source="full_catalog",
        )

    payload = exc.value.payload()
    unresolved = payload["unresolved"][0]
    assert unresolved["reason"] == "mapped_id_not_in_remote_catalog"
    assert unresolved["mapped_weightxreps_id"] == 157721
    assert unresolved["mapped_weightxreps_name"] == "Barbell Hip Thrust"
    assert unresolved["candidates"] == [
        {
            "weightxreps_id": 157700,
            "weightxreps_name": "Hip Thrust Machine",
            "match_reason": "similar_name",
        }
    ]


def test_mapping_without_id_resolves_by_canonical_remote_name():
    mappings = [
        ExerciseMapping(
            weightxreps_name="Barbell Hip Thrust",
            weightxreps_id=None,
            aliases=["Hip Thrust"],
        )
    ]

    resolved = resolve_exercise_ids(
        date="2026-06-20",
        exercise_names=["Hip Thrust"],
        local_mappings=mappings,
        remote_exercise_ids={"Barbell Hip Thrust": 157721},
    )

    assert resolved == {"Hip Thrust": 157721}


def test_create_if_missing_returns_new_exercise_marker_with_full_catalog():
    mappings = [
        ExerciseMapping(
            weightxreps_name="New Exercise Name",
            weightxreps_id=None,
            aliases=["New Exercise Name"],
            create_if_missing=True,
        )
    ]

    resolved = resolve_exercise_ids(
        date="2026-06-20",
        exercise_names=["New Exercise Name"],
        local_mappings=mappings,
        remote_exercise_ids={},
        catalog_source="full_catalog",
    )

    assert resolved == {"New Exercise Name": None}


def test_create_if_missing_requires_full_catalog():
    mappings = [
        ExerciseMapping(
            weightxreps_name="New Exercise Name",
            weightxreps_id=None,
            aliases=["New Exercise Name"],
            create_if_missing=True,
        )
    ]

    with pytest.raises(ExerciseResolutionRequired) as exc:
        resolve_exercise_ids(
            date="2026-06-20",
            exercise_names=["New Exercise Name"],
            local_mappings=mappings,
            remote_exercise_ids={},
            catalog_source="partial_jeditor",
        )

    payload = exc.value.payload()
    assert payload["catalog_source"] == "partial_jeditor"
    assert payload["unresolved"][0]["reason"] == "create_requires_full_catalog"


def test_create_if_missing_with_existing_id_resolves_to_id():
    mappings = [
        ExerciseMapping(
            weightxreps_name="New Exercise Name",
            weightxreps_id=157721,
            aliases=["New Exercise Name"],
            create_if_missing=True,
        )
    ]

    resolved = resolve_exercise_ids(
        date="2026-06-20",
        exercise_names=["New Exercise Name"],
        local_mappings=mappings,
        remote_exercise_ids={"New Exercise Name": 157721},
    )

    assert resolved == {"New Exercise Name": 157721}


def test_create_if_missing_with_existing_canonical_name_resolves_to_remote_id():
    mappings = [
        ExerciseMapping(
            weightxreps_name="New Exercise Name",
            weightxreps_id=None,
            aliases=["New Exercise Alias"],
            create_if_missing=True,
        )
    ]

    resolved = resolve_exercise_ids(
        date="2026-06-20",
        exercise_names=["New Exercise Alias"],
        local_mappings=mappings,
        remote_exercise_ids={"New Exercise Name": 157721},
    )

    assert resolved == {"New Exercise Alias": 157721}
