import pytest

from training_sync.domain.exercise_catalog import (
    ExerciseCatalog,
    ExerciseIdentity,
    ProviderBinding,
)
from training_sync.weightxreps.exercise_mapping import load_exercise_catalog, save_exercise_catalog


def test_catalog_uses_stable_key_and_resolves_alias_and_provider_binding():
    catalog = ExerciseCatalog(
        exercises=(
            ExerciseIdentity(
                key="chin_up",
                name="Chin Up",
                aliases=("Dominada supina",),
                providers={"weightxreps": ProviderBinding(name="Chin Up", remote_id=123)},
            ),
        )
    )

    assert catalog.resolve("dominada supina").key == "chin_up"
    assert catalog.resolve_provider("weightxreps", 123).key == "chin_up"


def test_catalog_rejects_normalized_collisions():
    with pytest.raises(ValueError, match="Duplicate exercise alias"):
        ExerciseCatalog(
            exercises=(
                ExerciseIdentity(key="chin_up", name="Chin Up", aliases=("Pull-up",)),
                ExerciseIdentity(key="pull_up", name="Pull Up", aliases=()),
            )
        )


def test_legacy_read_is_non_mutating_and_explicit_save_backs_up_and_reads_back(tmp_path):
    path = tmp_path / "weightxreps-exercises.toml"
    original = '[[exercises]]\nweightxreps_name = "Chin Up"\nweightxreps_id = 123\naliases = ["Pull Up"]\n'
    path.write_text(original, encoding="utf-8")

    catalog = load_exercise_catalog(path)
    assert path.read_text(encoding="utf-8") == original

    save_exercise_catalog(path, catalog)
    assert len(list(tmp_path.glob("weightxreps-exercises.toml.*.bak"))) == 1
    assert load_exercise_catalog(path).resolve("pull up").key == "chin_up"
