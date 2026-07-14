"""Parser for Weight x Reps-compatible text blocks."""

from dataclasses import dataclass, field
from decimal import Decimal
import re


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


@dataclass(frozen=True)
class ParsedExercise:
    name: str
    sets: list[ParsedSetLine] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedTrainingDay:
    date: str
    body_weight_kg: float | None
    exercises: list[ParsedExercise] = field(default_factory=list)


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
        exercises.append(_parse_exercise_block(current_name, current_lines))
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


def _parse_exercise_block(name: str, lines: list[str]) -> ParsedExercise:
    duration_line = next((line for line in lines if line.startswith(_DURATION_PREFIX)), None)
    if duration_line is None:
        return ParsedExercise(
            name=name,
            sets=[_parse_set_line(line) for line in lines if " x " in line],
        )

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
    weight_part, reps_part = [part.strip() for part in line.split(" x ", 1)]
    reps = tuple(int(rep.strip()) for rep in reps_part.split(","))
    if weight_part.upper() == "BW":
        return ParsedSetLine(weight_kg=0.0, reps=reps, uses_bodyweight=True)
    if weight_part.endswith("kg"):
        return ParsedSetLine(
            weight_kg=float(weight_part.removesuffix("kg")),
            reps=reps,
            uses_bodyweight=False,
        )
    raise ValueError(f"Unsupported set line: {line}")
