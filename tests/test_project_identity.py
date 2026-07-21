from pathlib import Path
import tomllib


def test_pyproject_exposes_only_training_sync_identity():
    project_root = Path(__file__).parents[1]
    metadata = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert metadata["name"] == "training-sync"
    assert metadata["version"] == "1.0.0"
    assert metadata["scripts"] == {"training-sync": "training_sync.cli:main"}
