import json
import subprocess
import sys


def test_cli_starts_on_the_running_python_version():
    result = subprocess.run(
        [sys.executable, "-c", "from training_sync.cli import main; main()", "--help"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "garmin" in result.stdout


def test_string_enums_preserve_string_representation_and_serialization():
    from training_sync.domain.reconciliation import OperationKind, TargetResultState
    from training_sync.domain.training import EffortScope, LoadKind

    values = [LoadKind.MASS, EffortScope.SET, OperationKind.CREATE, TargetResultState.VERIFIED]
    assert [str(value) for value in values] == ["mass", "set", "create", "verified"]
    assert [f"{value}" for value in values] == ["mass", "set", "create", "verified"]
    assert json.loads(json.dumps(values)) == ["mass", "set", "create", "verified"]
