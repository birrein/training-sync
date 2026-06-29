from training_sync.weightxreps.exercise_mapping import (
    ExerciseMapping,
    add_alias_mapping,
    load_exercise_mappings,
)


def test_add_alias_mapping_writes_deterministic_toml(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"

    add_alias_mapping(
        mapping_path,
        incoming_name="Barbell Hip Thrust with Bench",
        weightxreps_name="Barbell Hip Thrust",
        weightxreps_id=157721,
    )

    assert mapping_path.read_text(encoding="utf-8") == (
        '[[exercises]]\n'
        'weightxreps_name = "Barbell Hip Thrust"\n'
        'weightxreps_id = 157721\n'
        'aliases = [\n'
        '  "Barbell Hip Thrust",\n'
        '  "Barbell Hip Thrust with Bench",\n'
        ']\n'
    )
    assert load_exercise_mappings(mapping_path) == [
        ExerciseMapping(
            weightxreps_name="Barbell Hip Thrust",
            weightxreps_id=157721,
            aliases=["Barbell Hip Thrust", "Barbell Hip Thrust with Bench"],
        )
    ]


def test_add_alias_mapping_creates_backup_before_overwrite(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"
    mapping_path.write_text(
        '[[exercises]]\nweightxreps_name = "Chin Up"\nweightxreps_id = 10\naliases = ["Chin Up"]\n',
        encoding="utf-8",
    )

    add_alias_mapping(
        mapping_path,
        incoming_name="Pull Up",
        weightxreps_name="Chin Up",
        weightxreps_id=10,
    )

    backups = list(tmp_path.glob("weightxreps-exercises.toml.*.bak"))
    assert len(backups) == 1
    assert 'weightxreps_name = "Chin Up"' in backups[0].read_text(encoding="utf-8")


def test_add_alias_mapping_chmods_backup_and_target_to_user_only(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"
    mapping_path.write_text(
        '[[exercises]]\nweightxreps_name = "Chin Up"\nweightxreps_id = 10\naliases = ["Chin Up"]\n',
        encoding="utf-8",
    )
    mapping_path.chmod(0o644)

    add_alias_mapping(
        mapping_path,
        incoming_name="Pull Up",
        weightxreps_name="Chin Up",
        weightxreps_id=10,
    )

    backups = list(tmp_path.glob("weightxreps-exercises.toml.*.bak"))
    assert len(backups) == 1
    assert backups[0].stat().st_mode & 0o777 == 0o600
    assert mapping_path.stat().st_mode & 0o777 == 0o600


def test_add_alias_mapping_deduplicates_aliases_case_insensitively(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"
    mapping_path.write_text(
        '[[exercises]]\nweightxreps_name = "Chin Up"\nweightxreps_id = 10\naliases = ["pull up"]\n',
        encoding="utf-8",
    )

    add_alias_mapping(
        mapping_path,
        incoming_name="PULL UP",
        weightxreps_name="Chin Up",
        weightxreps_id=10,
    )

    assert load_exercise_mappings(mapping_path) == [
        ExerciseMapping(
            weightxreps_name="Chin Up",
            weightxreps_id=10,
            aliases=["Chin Up", "pull up"],
        )
    ]
