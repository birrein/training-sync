import ast
from importlib import import_module, resources
from pathlib import Path


def test_training_sync_garmin_auth_and_weight_modules_are_importable():
    for module_name in ("auth", "weight"):
        import_module(f"training_sync.garmin.{module_name}")


def test_training_sync_garmin_package_exposes_adapters_and_exercise_data():
    for module_name in (
        "fetch",
        "import_strength",
        "payloads",
        "exercise_mapping",
    ):
        import_module(f"training_sync.garmin.{module_name}")

    exercise_data = resources.files("training_sync.garmin").joinpath("garmin_exercises.json")
    assert exercise_data.is_file()
    assert exercise_data.read_text(encoding="utf-8").startswith("{")


def test_training_sync_source_does_not_import_legacy_namespace():
    package_root = Path(__file__).parents[1] / "src" / "training_sync"
    legacy_imports = []

    for source_path in package_root.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "garmin_sync":
                legacy_imports.append(f"{source_path.relative_to(package_root)}:{node.lineno}")
            elif isinstance(node, ast.Import):
                legacy_imports.extend(
                    f"{source_path.relative_to(package_root)}:{node.lineno}"
                    for alias in node.names
                    if alias.name.split(".")[0] == "garmin_sync"
                )

    assert legacy_imports == []
