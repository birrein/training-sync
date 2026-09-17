"""Human-readable previews for planned Garmin workouts."""

from __future__ import annotations

from typing import Any, Mapping

from training_sync.domain.planned_workout import PlannedWorkout
from training_sync.garmin.planned_workouts import project_planned_workout


def render_planned_workout(
    workout: PlannedWorkout,
    *,
    garmin_dict: Mapping[str, Mapping[str, Any]] | None = None,
    max_steps: int | None = None,
) -> str:
    """Render the expanded sequence and compact repeat layout for review.

    The returned text is produced by the same projection used for Garmin
    publication, so a compact payload never hides its physical sets or rests
    from the user.
    """

    return project_planned_workout(
        workout, garmin_dict=garmin_dict, max_steps=max_steps
    ).preview
