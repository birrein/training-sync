"""Parser for Weight x Reps-compatible text blocks."""

from dataclasses import dataclass, field
from decimal import Decimal
import re

from training_sync.domain.activity_classification import classify_activity_type


DISTANCE_UNIT_KILOMETERS = "km"
_DURATION_PREFIX = "@ Duration: "
_DISTANCE_PATTERN = re.compile(r"^(?P<distance>\d+(?:\.\d+)?)\s*(?P<unit>km)$")


@dataclass(frozen=True)
class ParsedSetLine:
    weight_kg: float = 0.0
    reps: tuple[int, ...] = ()
    uses_bodyweight: bool = False
    set_type: int = 0
    duration_ms: int | None = None
    distance: float | None = None
    distance_unit: str | None = None
    comment: str | None = None
    rpe: float | None = None


@dataclass(frozen=True)
class ParsedExercise:
    name: str
    sets: list[ParsedSetLine] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedTrainingDay:
    date: str
    body_weight_kg: float | None
    exercises: list[ParsedExercise] = field(default_factory=list)


def render_strength_text(day: ParsedTrainingDay) -> str | None:
    """Render the parseable strength/body-weight subset of a training day."""

    strength_exercises = [
        exercise
        for exercise in day.exercises
        if all(set_line.set_type == 0 for set_line in exercise.sets)
    ]
    if day.body_weight_kg is None and not strength_exercises:
        return None

    lines = [day.date]
    if day.body_weight_kg is not None:
        lines.append(f"@ {day.body_weight_kg:g} bw")
    for exercise in strength_exercises:
        lines.extend(("", f"#{exercise.name}"))
        lines.extend(_render_strength_set_line(set_line) for set_line in exercise.sets)
    return "\n".join(lines)


def validate_strength_round_trip(day: ParsedTrainingDay) -> None:
    """Reject preserved state that the daily strength grammar would alter."""

    expected = ParsedTrainingDay(
        date=day.date,
        body_weight_kg=day.body_weight_kg,
        exercises=[
            exercise
            for exercise in day.exercises
            if all(set_line.set_type == 0 for set_line in exercise.sets)
        ],
    )
    rendered = render_strength_text(expected)
    observed = (
        parse_weightxreps_text(rendered)
        if rendered is not None
        else ParsedTrainingDay(date=day.date, body_weight_kg=None)
    )
    if observed != expected:
        raise ValueError(
            "Remote strength snapshot is unrepresentable by the daily grammar "
            f"without round-trip loss: expected={expected!r}, observed={observed!r}"
        )


def _render_strength_set_line(set_line: ParsedSetLine) -> str:
    weight = "BW" if set_line.uses_bodyweight else f"{set_line.weight_kg:g}kg"
    reps = ", ".join(str(rep) for rep in set_line.reps)
    suffix = f" @{set_line.rpe:g} rpe" if set_line.rpe is not None else ""
    return f"{weight} x {reps}{suffix}"


def parse_weightxreps_text(text: str) -> ParsedTrainingDay:
    lines = [line.strip() for line in text.strip().splitlines()]
    date = lines[0]
    body_weight = None
    exercises: list[ParsedExercise] = []
    current_name: str | None = None
    current_lines: list[str] = []

    def finish_exercise() -> None:
        nonlocal current_name, current_lines
        if current_name is None:
            return
        exercise = _parse_exercise_block(current_name, current_lines)
        if exercise is not None:
            exercises.append(exercise)
        current_name = None
        current_lines = []

    for line in lines[1:]:
        if not line:
            continue
        if line.startswith("@ "):
            if current_name is None and line.endswith(" bw"):
                body_weight = float(line.removeprefix("@ ").removesuffix(" bw"))
                continue
        if line.startswith("#"):
            finish_exercise()
            current_name = line.removeprefix("#")
            continue
        if current_name is None:
            continue
        current_lines.append(line)

    finish_exercise()

    return ParsedTrainingDay(date=date, body_weight_kg=body_weight, exercises=exercises)


def _parse_exercise_block(name: str, lines: list[str]) -> ParsedExercise | None:
    duration_line = next((line for line in lines if line.startswith(_DURATION_PREFIX)), None)
    if duration_line is None:
        return ParsedExercise(
            name=name,
            sets=[_parse_set_line(line) for line in lines if not line.startswith("@ ")],
        )

    classification = classify_activity_type(name)
    if classification.local_only:
        return None
    name = classification.weightxreps_name
    if name is None:
        return None

    distance = None
    distance_unit = None
    comments: list[str] = []
    for line in lines:
        distance_match = _DISTANCE_PATTERN.fullmatch(line)
        if distance_match:
            distance = float(distance_match.group("distance"))
            distance_unit = distance_match.group("unit")
        elif line.startswith("@ ") and not line.startswith(_DURATION_PREFIX):
            comments.append(line.removeprefix("@ "))

    return ParsedExercise(
        name=name,
        sets=[
            ParsedSetLine(
                set_type=2 if distance is not None else 1,
                duration_ms=_parse_duration_ms(duration_line.removeprefix(_DURATION_PREFIX)),
                distance=distance,
                distance_unit=distance_unit,
                comment=" | ".join(comments) or None,
            )
        ],
    )


def _parse_duration_ms(value: str) -> int:
    hours_text, minutes_text, seconds_text = value.split(":", 2)
    total_seconds = (
        Decimal(hours_text) * 3600
        + Decimal(minutes_text) * 60
        + Decimal(seconds_text)
    )
    return int(total_seconds * 1000)


def _parse_set_line(line: str) -> ParsedSetLine:
    parts = [part.strip() for part in line.split(" x ", 1)]
    if len(parts) != 2:
        raise ValueError(f"Unsupported set line: {line}")
    weight_part, reps_part = parts
    rpe = None
    rpe_match = re.search(r"\s+@\s*(\d+(?:\.\d+)?)\s*rpe\s*$", reps_part, re.IGNORECASE)
    if rpe_match:
        rpe = float(rpe_match.group(1))
        reps_part = reps_part[: rpe_match.start()].strip()
    reps = tuple(int(rep.strip()) for rep in reps_part.split(","))
    if weight_part.upper() == "BW":
        return ParsedSetLine(weight_kg=0.0, reps=reps, uses_bodyweight=True, rpe=rpe)
    if weight_part.endswith("kg"):
        return ParsedSetLine(
            weight_kg=float(weight_part.removesuffix("kg")),
            reps=reps,
            uses_bodyweight=False,
            rpe=rpe,
        )
    raise ValueError(f"Unsupported set line: {line}")
