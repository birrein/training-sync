"""Local configuration paths for training-sync."""

import os
from pathlib import Path


def config_dir() -> Path:
    return Path.home() / ".config" / "training-sync"


def garmin_token_path() -> Path:
    return config_dir() / "garmin-token.json"


def weightxreps_token_path() -> Path:
    return config_dir() / "weightxreps-token.json"


def weightxreps_exercise_mapping_path() -> Path:
    return config_dir() / "weightxreps-exercises.toml"


def weightxreps_user_id_path() -> Path:
    return config_dir() / "weightxreps-user-id"


def load_weightxreps_user_id() -> int | None:
    raw_user_id = os.environ.get("WEIGHTXREPS_USER_ID")
    if raw_user_id is None:
        path = weightxreps_user_id_path()
        if not path.exists():
            return None
        raw_user_id = path.read_text(encoding="utf-8")

    raw_user_id = raw_user_id.strip()
    if not raw_user_id:
        return None

    try:
        return int(raw_user_id)
    except ValueError as exc:
        raise ValueError("Weight x Reps user id must be numeric") from exc
