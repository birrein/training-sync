"""Push a vault training day to Weight x Reps."""

from pathlib import Path

from training_sync.use_cases.weightxreps_preview import preview_weightxreps_day_from_vault


def push_weightxreps_day(
    vault_root: Path,
    date: str,
    client,
    exercise_ids: dict[str, int],
    yes: bool,
) -> str:
    if not exercise_ids and hasattr(client, "exercise_ids"):
        exercise_ids = client.exercise_ids(date)

    rows = preview_weightxreps_day_from_vault(vault_root, date, exercise_ids)
    exists = client.day_has_content(date)
    if exists and not yes:
        raise RuntimeError(f"Weight x Reps day {date} already has content; rerun with --yes to replace it")

    client.save_jeditor(rows)
    if not client.verify_day(date, rows):
        raise RuntimeError(f"Weight x Reps verification failed for {date}")

    return "replaced" if exists else "saved"
