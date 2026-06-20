"""Local configuration paths for training-sync."""

from pathlib import Path


def config_dir() -> Path:
    return Path.home() / ".config" / "training-sync"


def weightxreps_token_path() -> Path:
    return config_dir() / "weightxreps-token.json"
