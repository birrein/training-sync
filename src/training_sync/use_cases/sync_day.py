"""Preflight-first orchestration for one-day synchronization."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from training_sync.domain.garmin_activity import GarminActivity
from training_sync.renderers.garmin_daily import render_training_activities
from training_sync.use_cases.weightxreps_preview import preview_weightxreps_day_from_vault
from training_sync.vault.daily import daily_note_path
from training_sync.vault.training_block import (
    extract_training_section,
    replace_training_section,
    training_section_has_content,
)
from training_sync.weightxreps.exercise_mapping import ExerciseMapping


@dataclass(frozen=True)
class SyncDependencies:
    garmin: Any
    weightxreps: Any
    vault_root: Path
    mappings: list[ExerciseMapping]
    user_id: int | None


@dataclass(frozen=True)
class SyncPlan:
    date: str
    activities: tuple[GarminActivity, ...]
    daily_path: Path
    original_daily: str
    updated_daily: str
    weightxreps_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class SyncResult:
    date: str
    daily_path: Path
    activity_count: int
    weightxreps_verified: bool


def preflight_sync_day(date: str, *, yes: bool, deps: SyncDependencies) -> SyncPlan:
    raw_activities = deps.garmin.get_activities_by_date(date, date)
    activities = tuple(
        sorted(
            (GarminActivity.from_garmin(raw) for raw in raw_activities),
            key=lambda activity: (activity.start_time, activity.activity_id),
        )
    )
    if not activities:
        raise RuntimeError(f"No Garmin activities found for {date}")

    note_path = daily_note_path(deps.vault_root, date)
    if not note_path.exists():
        raise FileNotFoundError(f"Daily note not found: {note_path}")

    original_daily = note_path.read_text(encoding="utf-8")
    training_section = extract_training_section(original_daily)
    if training_section_has_content(original_daily) and not yes:
        raise RuntimeError(f"Daily training section for {date} has content; rerun with --yes to replace it")

    rendered_activities = render_training_activities(date, activities)
    updated_daily = replace_training_section(original_daily, rendered_activities)

    if deps.user_id is not None:
        exercise_ids = deps.weightxreps.exercise_catalog(deps.user_id)
        catalog_source = "full_catalog"
    else:
        exercise_ids = deps.weightxreps.exercise_ids(date)
        catalog_source = "partial_jeditor"

    if training_section:
        rows = tuple(
            preview_weightxreps_day_from_vault(
                deps.vault_root,
                date,
                exercise_ids=exercise_ids,
                exercise_mappings=deps.mappings,
                catalog_source=catalog_source,
            )
        )
    else:
        rows = ()

    if deps.weightxreps.day_has_content(date) and not yes:
        raise RuntimeError(f"Weight x Reps day {date} has content; rerun with --yes to replace it")

    return SyncPlan(
        date=date,
        activities=activities,
        daily_path=note_path,
        original_daily=original_daily,
        updated_daily=updated_daily,
        weightxreps_rows=rows,
    )


def write_daily(plan: SyncPlan) -> None:
    plan.daily_path.write_text(plan.updated_daily, encoding="utf-8")


def apply_sync_plan(plan: SyncPlan, *, deps: SyncDependencies) -> SyncResult:
    write_daily(plan)
    rows = list(plan.weightxreps_rows)
    deps.weightxreps.save_jeditor(rows)
    verified = deps.weightxreps.verify_day(plan.date, rows)
    if verified is False:
        raise RuntimeError(f"Weight x Reps verification failed for {plan.date}")
    return SyncResult(
        date=plan.date,
        daily_path=plan.daily_path,
        activity_count=len(plan.activities),
        weightxreps_verified=True,
    )


def sync_day(date: str, *, yes: bool, deps: SyncDependencies) -> SyncResult:
    plan = preflight_sync_day(date, yes=yes, deps=deps)
    return apply_sync_plan(plan, deps=deps)
