"""Local configuration paths for training-sync."""

import os
from pathlib import Path


def config_dir() -> Path:
    return Path.home() / ".config" / "training-sync"


def vault_root_path() -> Path:
    return config_dir() / "vault-root"


def _load_local_setting(environment_name: str, local_path: Path) -> str | None:
    configured_value = os.environ.get(environment_name)
    if configured_value is None or not configured_value.strip():
        if not local_path.exists():
            return None
        configured_value = local_path.read_text(encoding="utf-8")

    configured_value = configured_value.strip()
    return configured_value or None


def vault_root() -> Path:
    """Return the local Obsidian vault root using env-over-local precedence."""
    configured_root = _load_local_setting("TRAINING_SYNC_VAULT_ROOT", vault_root_path())
    if configured_root is None:
        raise ValueError(
            "Obsidian vault root is not configured. Set TRAINING_SYNC_VAULT_ROOT or "
            f"save the absolute vault path in {vault_root_path()}."
        )

    root = Path(configured_root).expanduser()
    if not root.is_absolute():
        raise ValueError(
            "Obsidian vault root must be an absolute path. "
            "Set TRAINING_SYNC_VAULT_ROOT or update the local vault-root file."
        )
    return root


def garmin_token_path() -> Path:
    return config_dir() / "garmin-token.json"


def planned_workout_journal_path() -> Path:
    """Return the local journal used for planned-workout recovery."""
    return config_dir() / "planned-workouts.json"


def weightxreps_token_path() -> Path:
    return config_dir() / "weightxreps-token.json"


def weightxreps_exercise_mapping_path() -> Path:
    return config_dir() / "weightxreps-exercises.toml"


def weightxreps_user_id_path() -> Path:
    return config_dir() / "weightxreps-user-id"


def intervals_api_key_path() -> Path:
    return config_dir() / "intervals-api-key"


def load_intervals_api_key() -> str | None:
    value = os.environ.get("INTERVALS_API_KEY")
    if value is None:
        path = intervals_api_key_path()
        value = path.read_text(encoding="utf-8") if path.exists() else None
    return value.strip() if value and value.strip() else None


def load_weightxreps_user_id() -> int | None:
    raw_user_id = _load_local_setting("WEIGHTXREPS_USER_ID", weightxreps_user_id_path())
    if raw_user_id is None:
        return None

    try:
        return int(raw_user_id)
    except ValueError as exc:
        raise ValueError("Weight x Reps user id must be numeric") from exc
