"""Parser for Weight x Reps-compatible text blocks."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedSetLine:
    weight_kg: float
    reps: list[int]
    uses_bodyweight: bool = False


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
    current: ParsedExercise | None = None

    for line in lines[1:]:
        if not line:
            continue
        if line.startswith("@ "):
            if line.endswith(" bw"):
                body_weight = float(line.removeprefix("@ ").removesuffix(" bw"))
            continue
        if line.startswith("#"):
            current = ParsedExercise(name=line.removeprefix("#"))
            exercises.append(current)
            continue
        if current is None:
            continue
        current.sets.append(_parse_set_line(line))

    return ParsedTrainingDay(date=date, body_weight_kg=body_weight, exercises=exercises)


def _parse_set_line(line: str) -> ParsedSetLine:
    weight_part, reps_part = [part.strip() for part in line.split(" x ", 1)]
    reps = [int(rep.strip()) for rep in reps_part.split(",")]
    if weight_part.upper() == "BW":
        return ParsedSetLine(weight_kg=0.0, reps=reps, uses_bodyweight=True)
    if weight_part.endswith("kg"):
        return ParsedSetLine(
            weight_kg=float(weight_part.removesuffix("kg")),
            reps=reps,
            uses_bodyweight=False,
        )
    raise ValueError(f"Unsupported set line: {line}")
