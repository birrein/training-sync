"""Local configuration paths for training-sync."""

from pathlib import Path


def config_dir() -> Path:
    return Path.home() / ".config" / "training-sync"


def garmin_token_path() -> Path:
    return config_dir() / "garmin-token.json"


def weightxreps_token_path() -> Path:
    return config_dir() / "weightxreps-token.json"


def weightxreps_exercise_mapping_path() -> Path:
    return config_dir() / "weightxreps-exercises.toml"
