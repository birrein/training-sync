import tomllib
from pathlib import Path


def test_pyproject_exposes_only_training_sync_identity():
    project_root = Path(__file__).parents[1]
    metadata = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    lock = tomllib.loads((project_root / "uv.lock").read_text(encoding="utf-8"))

    assert metadata["name"] == "training-sync"
    assert metadata["version"] == "1.0.0"
    assert metadata["requires-python"] == ">=3.12"
    assert lock["requires-python"] == metadata["requires-python"]
    assert not any(dependency.startswith("tomli") for dependency in metadata["dependencies"])
    assert metadata["scripts"] == {"training-sync": "training_sync.cli:main"}
