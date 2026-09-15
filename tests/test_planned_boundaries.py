from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
PLANNED_MODULES = (
    PROJECT_ROOT / "src/training_sync/domain/planned_workout.py",
    PROJECT_ROOT / "src/training_sync/garmin/planned_workouts.py",
    PROJECT_ROOT / "src/training_sync/renderers/planned_workout.py",
    PROJECT_ROOT / "src/training_sync/use_cases/publish_workout.py",
    PROJECT_ROOT / "src/training_sync/use_cases/manage_planned_workouts.py",
)


def test_planned_lifecycle_does_not_import_other_writes_or_device_push():
    forbidden_modules = {
        "training_sync.vault",
        "training_sync.weightxreps",
        "garmin_sync",
    }
    forbidden_symbols = {
        "push_workout_to_device",
        "set_activity_exercise_sets",
        "set_activity_name",
        "saveJEditor",
    }
    violations = []
    for source_path in PLANNED_MODULES:
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_modules or alias.name.startswith("training_sync.vault"):
                        violations.append(f"{source_path}:{node.lineno}:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module in forbidden_modules or module.startswith("training_sync.vault"):
                    violations.append(f"{source_path}:{node.lineno}:{module}")
                for alias in node.names:
                    if alias.name in forbidden_symbols:
                        violations.append(f"{source_path}:{node.lineno}:{alias.name}")
            elif isinstance(node, ast.Name) and node.id in forbidden_symbols:
                violations.append(f"{source_path}:{node.lineno}:{node.id}")
    assert violations == []


def test_device_compatibility_is_not_claimed_by_planned_workout_docs():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    smoke = (PROJECT_ROOT / "docs/planned-garmin-device-smoke-test.md").read_text(encoding="utf-8")

    for text in (readme, smoke):
        assert "read-back" in text
        assert "unverified" in text
        assert "device" in text.lower()
    assert "watch or" in readme and "Edge" in readme
