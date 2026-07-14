"""Preflight-first orchestration for one-day synchronization."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from training_sync.domain.garmin_activity import GarminActivity
from training_sync.renderers.garmin_daily import render_training_activities
from training_sync.renderers.weightxreps_text import (
    DISTANCE_UNIT_KILOMETERS,
    ParsedExercise,
    ParsedSetLine,
    ParsedTrainingDay,
)
from training_sync.use_cases.weightxreps_preview import load_weightxreps_day_from_vault
from training_sync.vault.daily import daily_note_path
from training_sync.vault.training_block import (
    extract_training_section,
    replace_training_section,
    training_section_has_content,
)
from training_sync.weightxreps.exercise_mapping import ExerciseMapping
from training_sync.weightxreps.exercise_resolution import resolve_exercise_ids
from training_sync.weightxreps.jeditor import build_jeditor_rows


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


def build_complete_training_day(
    date: str,
    preserved: ParsedTrainingDay,
    activities: Sequence[GarminActivity],
) -> ParsedTrainingDay:
    exercises = [
        exercise
        for exercise in preserved.exercises
        if all(set_line.set_type == 0 for set_line in exercise.sets)
    ]
    for activity in activities:
        has_distance = activity.distance_m is not None
        exercises.append(
            ParsedExercise(
                name=_activity_exercise_name(activity.type_key),
                sets=[
                    ParsedSetLine(
                        set_type=2 if has_distance else 1,
                        duration_ms=activity.duration_ms,
                        distance=activity.distance_m / 1000 if has_distance else None,
                        distance_unit=DISTANCE_UNIT_KILOMETERS if has_distance else None,
                        comment=_activity_comment(activity),
                    )
                ],
            )
        )
    return ParsedTrainingDay(
        date=date,
        body_weight_kg=preserved.body_weight_kg,
        exercises=exercises,
    )


def _activity_exercise_name(type_key: str) -> str:
    if "run" in type_key:
        return "Running"
    if "cycl" in type_key or "ride" in type_key:
        return "Cycling"
    return type_key.capitalize()


def _activity_comment(activity: GarminActivity) -> str:
    parts = [activity.name]
    metrics = (
        ("Avg HR", activity.average_hr, ""),
        ("Max HR", activity.max_hr, ""),
        ("Elev Gain", activity.elevation_gain_m, " m"),
        ("Avg Power", activity.average_power_w, " W"),
        ("Calories", activity.calories, ""),
        ("Training Load", activity.training_load, ""),
    )
    parts.extend(
        f"{label}: {value:g}{suffix}"
        for label, value, suffix in metrics
        if value is not None
    )
    return " | ".join(parts)


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

    preserved = (
        load_weightxreps_day_from_vault(deps.vault_root, date)
        if training_section
        else ParsedTrainingDay(date=date, body_weight_kg=None)
    )
    complete_day = build_complete_training_day(date, preserved, activities)
    resolved_exercise_ids = resolve_exercise_ids(
        date=date,
        exercise_names=[exercise.name for exercise in complete_day.exercises],
        local_mappings=deps.mappings,
        remote_exercise_ids=exercise_ids,
        catalog_source=catalog_source,
    )
    rows = tuple(build_jeditor_rows(complete_day, resolved_exercise_ids))

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
