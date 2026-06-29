"""Preview Weight x Reps rows from a vault daily note."""

from pathlib import Path
from typing import Any

from training_sync.renderers.weightxreps_text import ParsedTrainingDay, parse_weightxreps_text
from training_sync.vault.daily import daily_note_path
from training_sync.vault.training_block import extract_training_section
from training_sync.weightxreps.exercise_mapping import ExerciseMapping
from training_sync.weightxreps.exercise_resolution import resolve_exercise_ids
from training_sync.weightxreps.jeditor import build_jeditor_rows


def preview_weightxreps_day_from_vault(
    vault_root: Path,
    date: str,
    exercise_ids: dict[str, int],
    exercise_mappings: list[ExerciseMapping] | None = None,
    catalog_source: str = "partial_jeditor",
) -> list[dict[str, Any]]:
    parsed = load_weightxreps_day_from_vault(vault_root, date)
    resolved_exercise_ids = resolve_exercise_ids(
        date=date,
        exercise_names=[exercise.name for exercise in parsed.exercises],
        local_mappings=exercise_mappings or [],
        remote_exercise_ids=exercise_ids,
        catalog_source=catalog_source,
    )
    return build_jeditor_rows(parsed, resolved_exercise_ids)


def load_weightxreps_day_from_vault(vault_root: Path, date: str) -> ParsedTrainingDay:
    note_path = daily_note_path(vault_root, date)
    if not note_path.exists():
        raise FileNotFoundError(f"Daily note not found: {note_path}")

    training_section = extract_training_section(note_path.read_text(encoding="utf-8"))
    text_block = _extract_first_text_block(training_section)
    return parse_weightxreps_text(text_block)


def _extract_first_text_block(markdown: str) -> str:
    fence = "```text"
    start = markdown.find(fence)
    if start == -1:
        raise ValueError("Training text block not found")
    content_start = start + len(fence)
    end = markdown.find("```", content_start)
    if end == -1:
        raise ValueError("Training text block is not closed")
    return markdown[content_start:end].strip()
