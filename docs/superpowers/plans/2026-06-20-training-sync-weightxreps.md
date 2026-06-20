# Training Sync Weight x Reps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first real `training-sync` integration that can sync one training day from Garmin to the vault and then write that day to Weight x Reps with OAuth-backed GraphQL.

**Architecture:** Add a new `training_sync` package while keeping `garmin_sync` compatibility wrappers. Use modular use cases plus concrete adapters: Garmin, vault, Weight x Reps, domain models, and renderers. Implement write paths only after preview, parsing, and verification are covered by tests.

**Tech Stack:** Python 3.14, argparse, requests, garminconnect, pytest, local filesystem for Obsidian daily notes, Weight x Reps OAuth2 PKCE and GraphQL.

---

## Source References

- Weight x Reps server README: GraphQL endpoint `/api/graphql`, OAuth endpoint `/api/auth`, and `saveJEditor` docs.
- Weight x Reps OAuth docs: Authorization Code Flow with PKCE, max `code_verifier` length 64, `S256` or `plain`, protected GraphQL calls use `Authorization: Bearer access_token`.
- Weight x Reps `JEditorSaveRow` docs: day rows, bodyweight rows, new exercise rows, exercise blocks, and set rows.
- Existing design spec: `docs/superpowers/specs/2026-06-20-training-sync-weightxreps-design.md`.

## File Structure

Create the new package:

```text
src/training_sync/
  __init__.py
  cli.py
  config.py
  domain/
    __init__.py
    body_weight.py
    strength_workout.py
    training_entry.py
  garmin/
    __init__.py
    auth.py
    client.py
    exercise_mapping.py
    payloads.py
  vault/
    __init__.py
    daily.py
    training_block.py
  weightxreps/
    __init__.py
    auth.py
    client.py
    jeditor.py
  renderers/
    __init__.py
    obsidian_markdown.py
    weightxreps_text.py
  use_cases/
    __init__.py
    import_fitbod_strength.py
    sync_day.py
```

Keep compatibility wrappers in existing `src/garmin_sync/` files until the migration is complete.

Create or modify tests:

```text
tests/test_training_sync_cli.py
tests/test_domain_training_entry.py
tests/test_vault_training_block.py
tests/test_weightxreps_jeditor.py
tests/test_weightxreps_auth.py
tests/test_weightxreps_client.py
tests/test_use_case_sync_day.py
tests/test_use_case_import_fitbod_strength.py
```

Existing tests must continue passing.

---

### Task 1: Add `training-sync` CLI Entry Point and Compatibility Wrapper

**Files:**
- Modify: `pyproject.toml`
- Create: `src/training_sync/__init__.py`
- Create: `src/training_sync/cli.py`
- Modify: `src/garmin_sync/cli.py`
- Test: `tests/test_training_sync_cli.py`

- [ ] **Step 1: Write the failing CLI tests**

Create `tests/test_training_sync_cli.py`:

```python
import sys

from training_sync import cli


def test_training_sync_garmin_fetch_dispatches_to_existing_fetch(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["training-sync", "garmin", "fetch", "2026-06-19"])
    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(
        cli,
        "fetch_and_print_activities",
        lambda client, date: calls.append(("fetch", client, date)),
    )

    cli.main()

    assert calls == [("fetch", "client", "2026-06-19")]


def test_training_sync_weight_command_dispatches_to_existing_weight(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["training-sync", "garmin", "weight", "2026-06-19"])
    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(
        cli,
        "print_weight_tag",
        lambda client, date: calls.append(("weight", client, date)),
    )

    cli.main()

    assert calls == [("weight", "client", "2026-06-19")]


def test_legacy_garmin_sync_cli_still_uses_training_sync_main(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["garmin-sync", "--weight", "2026-06-19"])
    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(
        cli,
        "print_weight_tag",
        lambda client, date: calls.append(("legacy-weight", client, date)),
    )

    cli.main()

    assert calls == [("legacy-weight", "client", "2026-06-19")]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_training_sync_cli.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'training_sync'`.

- [ ] **Step 3: Add the new package and CLI**

Create `src/training_sync/__init__.py`:

```python
"""Training synchronization across Garmin, Obsidian, and Weight x Reps."""
```

Create `src/training_sync/cli.py`:

```python
"""Command-line interface for training-sync."""

import argparse
import os
import sys

from garmin_sync.auth import get_client
from garmin_sync.commands.fetch import fetch_and_print_activities
from garmin_sync.commands.push import parse_workout, push_workout
from garmin_sync.commands.weight import print_weight_tag


def main() -> None:
    parser = argparse.ArgumentParser(
        prog=_program_name(),
        description="Sync training data across Garmin, Obsidian, and Weight x Reps.",
    )
    parser.add_argument("json_string", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("--fetch", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--weight", type=str, help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(dest="command")
    garmin = subparsers.add_parser("garmin", help="Garmin Connect commands")
    garmin_subparsers = garmin.add_subparsers(dest="garmin_command")

    garmin_fetch = garmin_subparsers.add_parser("fetch", help="Fetch Garmin activities")
    garmin_fetch.add_argument("date")

    garmin_weight = garmin_subparsers.add_parser("weight", help="Print Garmin body-weight tag")
    garmin_weight.add_argument("date")

    garmin_import = garmin_subparsers.add_parser("import-strength", help="Import strength JSON to Garmin")
    garmin_import.add_argument("json_file")

    args = parser.parse_args()
    client = get_client()

    if args.fetch:
        fetch_and_print_activities(client, args.fetch)
        return

    if args.weight:
        print_weight_tag(client, args.weight)
        return

    if args.json_string:
        _push_json_argument(client, args.json_string)
        return

    if args.command == "garmin" and args.garmin_command == "fetch":
        fetch_and_print_activities(client, args.date)
        return

    if args.command == "garmin" and args.garmin_command == "weight":
        print_weight_tag(client, args.date)
        return

    if args.command == "garmin" and args.garmin_command == "import-strength":
        _push_json_argument(client, args.json_file)
        return

    parser.print_help()


def _program_name() -> str:
    return os.path.basename(sys.argv[0]) or "training-sync"


def _push_json_argument(client, json_arg: str) -> None:
    try:
        if os.path.isfile(json_arg):
            with open(json_arg, "r", encoding="utf-8") as handle:
                workout_data = parse_workout(handle.read())
        else:
            workout_data = parse_workout(json_arg)
    except ValueError as exc:
        sys.exit(f"Data error: {exc}")

    push_workout(client, workout_data)
```

Modify `src/garmin_sync/cli.py`:

```python
"""Backward-compatible garmin-sync CLI entrypoint."""

from training_sync.cli import main


if __name__ == "__main__":
    main()
```

Modify `pyproject.toml` script section:

```toml
[project.scripts]
garmin-sync = "garmin_sync.cli:main"
training-sync = "training_sync.cli:main"
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_training_sync_cli.py tests/test_cli.py tests/test_parser.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/training_sync/__init__.py src/training_sync/cli.py src/garmin_sync/cli.py tests/test_training_sync_cli.py
git commit -m "feat(cli): add training-sync command group"
```

---

### Task 2: Move Domain Models to `training_sync.domain`

**Files:**
- Create: `src/training_sync/domain/__init__.py`
- Create: `src/training_sync/domain/strength_workout.py`
- Create: `src/training_sync/domain/body_weight.py`
- Create: `src/training_sync/domain/training_entry.py`
- Modify: `src/garmin_sync/workouts.py`
- Modify: `src/garmin_sync/commands/weight.py`
- Test: `tests/test_domain_training_entry.py`

- [ ] **Step 1: Write failing domain tests**

Create `tests/test_domain_training_entry.py`:

```python
from training_sync.domain.body_weight import WeightReading, format_weight_tag
from training_sync.domain.strength_workout import (
    StrengthExercise,
    StrengthSet,
    StrengthWorkout,
    strength_workout_from_dict,
)
from training_sync.domain.training_entry import ActivityMetric, TrainingEntry


def test_strength_workout_from_dict_normalizes_fitbod_payload():
    workout = strength_workout_from_dict(
        {
            "date": "2026-06-19",
            "title": "Upper Body Day 2",
            "exercises": [
                {
                    "name": "Barbell Row",
                    "sets": [
                        {"reps": 8, "weight": 31},
                        {"reps": 12, "weight": 51},
                    ],
                }
            ],
        }
    )

    assert workout == StrengthWorkout(
        date="2026-06-19",
        title="Upper Body Day 2",
        exercises=[
            StrengthExercise(
                name="Barbell Row",
                sets=[
                    StrengthSet(reps=8, weight_kg=31.0),
                    StrengthSet(reps=12, weight_kg=51.0),
                ],
            )
        ],
    )


def test_weight_reading_formats_weightxreps_tag():
    reading = WeightReading(
        calendar_date="2026-06-18",
        weight_kg=71.389,
        source_type="INDEX_SCALE",
        day_delta=-1,
    )

    assert format_weight_tag(reading) == "@ 71.4 bw"


def test_training_entry_holds_activity_metrics():
    entry = TrainingEntry(
        date="2026-06-19",
        title="Upper Body Day 2",
        activity_type="strength_training",
        metrics=[
            ActivityMetric(label="Duration", value="01:11:20.3"),
            ActivityMetric(label="Avg HR", value="90"),
        ],
        body_weight=71.4,
        text_block="#Chin Up\nBW x 5, 5, 5",
    )

    assert entry.title == "Upper Body Day 2"
    assert entry.body_weight == 71.4
    assert entry.metrics[0].label == "Duration"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_domain_training_entry.py -v
```

Expected: FAIL with missing `training_sync.domain` modules.

- [ ] **Step 3: Create domain modules**

Create `src/training_sync/domain/__init__.py`:

```python
"""Pure training-sync domain objects."""
```

Create `src/training_sync/domain/strength_workout.py` by moving the current content of `src/garmin_sync/workouts.py`:

```python
"""Strength workout domain objects and input normalization."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class StrengthSet:
    reps: int
    weight_kg: float


@dataclass(frozen=True)
class StrengthExercise:
    name: str
    sets: list[StrengthSet]


@dataclass(frozen=True)
class StrengthWorkout:
    date: str
    title: str | None
    exercises: list[StrengthExercise]


def strength_workout_from_dict(
    workout_data: dict[str, Any],
    default_date: str | None = None,
) -> StrengthWorkout:
    date = (
        workout_data.get("date")
        or default_date
        or datetime.today().strftime("%Y-%m-%d")
    )
    exercises = [
        StrengthExercise(
            name=exercise.get("name", "UNKNOWN"),
            sets=[
                StrengthSet(
                    reps=int(raw_set.get("reps", 0)),
                    weight_kg=float(raw_set.get("weight", 0)),
                )
                for raw_set in exercise.get("sets", [])
            ],
        )
        for exercise in workout_data.get("exercises", [])
    ]

    return StrengthWorkout(
        date=date,
        title=workout_data.get("title"),
        exercises=exercises,
    )
```

Create `src/training_sync/domain/body_weight.py`:

```python
"""Body-weight domain objects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WeightReading:
    calendar_date: str
    weight_kg: float
    source_type: str | None
    day_delta: int


def format_weight_tag(reading: WeightReading) -> str:
    return f"@ {reading.weight_kg:.1f} bw"
```

Create `src/training_sync/domain/training_entry.py`:

```python
"""Normalized training log entries."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActivityMetric:
    label: str
    value: str


@dataclass(frozen=True)
class TrainingEntry:
    date: str
    title: str
    activity_type: str
    metrics: list[ActivityMetric] = field(default_factory=list)
    body_weight: float | None = None
    text_block: str | None = None
```

Modify `src/garmin_sync/workouts.py` to a compatibility wrapper:

```python
"""Backward-compatible imports for strength workout domain objects."""

from training_sync.domain.strength_workout import (
    StrengthExercise,
    StrengthSet,
    StrengthWorkout,
    strength_workout_from_dict,
)

__all__ = [
    "StrengthExercise",
    "StrengthSet",
    "StrengthWorkout",
    "strength_workout_from_dict",
]
```

Modify `src/garmin_sync/commands/weight.py` to import `WeightReading` and `format_weight_tag` from `training_sync.domain.body_weight`, deleting the local dataclass and formatter.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_domain_training_entry.py tests/test_strength_workout_plan.py tests/test_weight.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/domain src/garmin_sync/workouts.py src/garmin_sync/commands/weight.py tests/test_domain_training_entry.py
git commit -m "refactor(domain): introduce training domain models"
```

---

### Task 3: Add Vault Daily Block Adapter

**Files:**
- Create: `src/training_sync/vault/__init__.py`
- Create: `src/training_sync/vault/daily.py`
- Create: `src/training_sync/vault/training_block.py`
- Test: `tests/test_vault_training_block.py`

- [ ] **Step 1: Write failing vault tests**

Create `tests/test_vault_training_block.py`:

```python
from pathlib import Path

import pytest

from training_sync.vault.daily import daily_note_path
from training_sync.vault.training_block import extract_training_section, replace_training_section


def test_daily_note_path_uses_existing_vault_pattern():
    path = daily_note_path(Path("/vault"), "2026-06-19")

    assert path == Path("/vault/daily/2026/06-June/2026-06-19-Friday.md")


def test_extract_training_section_returns_only_training_content():
    note = """# Friday

## ✅ Tasks

## 🏃 Training
- Upper Body Day 2
```text
2026-06-19
```

## 📚 Reading & Study
"""

    assert extract_training_section(note) == """- Upper Body Day 2
```text
2026-06-19
```"""


def test_replace_training_section_preserves_surrounding_note():
    note = """# Friday

## ✅ Tasks

## 🏃 Training

## 📚 Reading & Study
"""

    updated = replace_training_section(note, "- Santiago Running\n```text\n2026-06-19\n```")

    assert "## ✅ Tasks" in updated
    assert "## 📚 Reading & Study" in updated
    assert "- Santiago Running" in updated


def test_replace_training_section_requires_existing_heading():
    with pytest.raises(ValueError, match="Training section not found"):
        replace_training_section("# Friday\n", "- Activity")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_vault_training_block.py -v
```

Expected: FAIL with missing `training_sync.vault` modules.

- [ ] **Step 3: Implement vault modules**

Create `src/training_sync/vault/__init__.py`:

```python
"""Obsidian vault adapters."""
```

Create `src/training_sync/vault/daily.py`:

```python
"""Daily note path helpers."""

from datetime import date
from pathlib import Path

MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def daily_note_path(vault_root: Path, date_str: str) -> Path:
    day = date.fromisoformat(date_str)
    month_dir = f"{day.month:02d}-{MONTH_NAMES[day.month]}"
    weekday = day.strftime("%A")
    return vault_root / "daily" / str(day.year) / month_dir / f"{date_str}-{weekday}.md"
```

Create `src/training_sync/vault/training_block.py`:

```python
"""Read and update the ## 🏃 Training section in daily notes."""

TRAINING_HEADING = "## 🏃 Training"


def extract_training_section(note_text: str) -> str:
    start, end = _section_bounds(note_text)
    return note_text[start:end].strip()


def replace_training_section(note_text: str, new_content: str) -> str:
    start, end = _section_bounds(note_text)
    prefix = note_text[:start]
    suffix = note_text[end:]
    content = new_content.strip()
    return f"{prefix}{content}\n\n{suffix.lstrip()}"


def _section_bounds(note_text: str) -> tuple[int, int]:
    heading_index = note_text.find(TRAINING_HEADING)
    if heading_index == -1:
        raise ValueError("Training section not found")

    content_start = heading_index + len(TRAINING_HEADING)
    if note_text[content_start:content_start + 1] == "\n":
        content_start += 1

    next_heading = note_text.find("\n## ", content_start)
    if next_heading == -1:
        return content_start, len(note_text)

    return content_start, next_heading + 1
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_vault_training_block.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/vault tests/test_vault_training_block.py
git commit -m "feat(vault): add daily training block adapter"
```

---

### Task 4: Parse Weight x Reps Text Blocks

**Files:**
- Create: `src/training_sync/renderers/__init__.py`
- Create: `src/training_sync/renderers/weightxreps_text.py`
- Test: `tests/test_weightxreps_text.py`

- [ ] **Step 1: Write failing parser tests**

Create `tests/test_weightxreps_text.py`:

```python
from training_sync.renderers.weightxreps_text import (
    ParsedExercise,
    ParsedSetLine,
    ParsedTrainingDay,
    parse_weightxreps_text,
)


def test_parse_weightxreps_text_handles_bodyweight_and_weighted_sets():
    parsed = parse_weightxreps_text(
        """2026-06-19
@ 71.4 bw
@ Duration: 01:11:20.3

#Chin Up
BW x 5, 5, 5

#Barbell Row
31kg x 8
51kg x 12, 12, 12
"""
    )

    assert parsed == ParsedTrainingDay(
        date="2026-06-19",
        body_weight_kg=71.4,
        exercises=[
            ParsedExercise(
                name="Chin Up",
                sets=[ParsedSetLine(weight_kg=0.0, reps=[5, 5, 5], uses_bodyweight=True)],
            ),
            ParsedExercise(
                name="Barbell Row",
                sets=[
                    ParsedSetLine(weight_kg=31.0, reps=[8], uses_bodyweight=False),
                    ParsedSetLine(weight_kg=51.0, reps=[12, 12, 12], uses_bodyweight=False),
                ],
            ),
        ],
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_weightxreps_text.py -v
```

Expected: FAIL with missing `training_sync.renderers.weightxreps_text`.

- [ ] **Step 3: Implement parser**

Create `src/training_sync/renderers/__init__.py`:

```python
"""Renderers and parsers for training log text formats."""
```

Create `src/training_sync/renderers/weightxreps_text.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_weightxreps_text.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/renderers tests/test_weightxreps_text.py
git commit -m "feat(weightxreps): parse training text blocks"
```

---

### Task 5: Convert Parsed Training Days to JEditor Rows

**Files:**
- Create: `src/training_sync/weightxreps/__init__.py`
- Create: `src/training_sync/weightxreps/jeditor.py`
- Test: `tests/test_weightxreps_jeditor.py`

- [ ] **Step 1: Write failing JEditor tests**

Create `tests/test_weightxreps_jeditor.py`:

```python
from training_sync.renderers.weightxreps_text import (
    ParsedExercise,
    ParsedSetLine,
    ParsedTrainingDay,
)
from training_sync.weightxreps.jeditor import build_jeditor_rows


def test_build_jeditor_rows_uses_known_exercise_ids_and_bodyweight():
    day = ParsedTrainingDay(
        date="2026-06-19",
        body_weight_kg=71.4,
        exercises=[
            ParsedExercise(
                name="Chin Up",
                sets=[ParsedSetLine(weight_kg=0.0, reps=[5, 5, 5], uses_bodyweight=True)],
            ),
            ParsedExercise(
                name="Barbell Row",
                sets=[ParsedSetLine(weight_kg=51.0, reps=[12, 12, 12])],
            ),
        ],
    )

    rows = build_jeditor_rows(day, exercise_ids={"Chin Up": 10, "Barbell Row": 20})

    assert rows == [
        {"bw": 71.4, "lb": 0},
        {
            "on": "2026-06-19",
            "did": [
                {
                    "eid": 10,
                    "erows": [{"w": {"v": 0.0, "lb": 0, "usebw": 1}, "r": 5, "s": 3}],
                },
                {
                    "eid": 20,
                    "erows": [{"w": {"v": 51.0, "lb": 0}, "r": 12, "s": 3}],
                },
            ],
        },
    ]


def test_build_jeditor_rows_can_create_unknown_exercises():
    day = ParsedTrainingDay(
        date="2026-06-19",
        body_weight_kg=None,
        exercises=[
            ParsedExercise(
                name="New Lift",
                sets=[ParsedSetLine(weight_kg=10.0, reps=[8])],
            )
        ],
    )

    rows = build_jeditor_rows(day, exercise_ids={})

    assert rows == [
        {"newExercise": "New Lift"},
        {
            "on": "2026-06-19",
            "did": [
                {
                    "newExercise": "New Lift",
                    "erows": [{"w": {"v": 10.0, "lb": 0}, "r": 8, "s": 1}],
                }
            ],
        },
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_weightxreps_jeditor.py -v
```

Expected: FAIL with missing `training_sync.weightxreps`.

- [ ] **Step 3: Implement JEditor conversion**

Create `src/training_sync/weightxreps/__init__.py`:

```python
"""Weight x Reps adapters."""
```

Create `src/training_sync/weightxreps/jeditor.py`:

```python
"""Build Weight x Reps JEditorSaveRow payloads."""

from collections import Counter
from typing import Any

from training_sync.renderers.weightxreps_text import ParsedSetLine, ParsedTrainingDay


def build_jeditor_rows(
    day: ParsedTrainingDay,
    exercise_ids: dict[str, int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if day.body_weight_kg is not None:
        rows.append({"bw": day.body_weight_kg, "lb": 0})

    did = []
    for exercise in day.exercises:
        exercise_row: dict[str, Any]
        if exercise.name in exercise_ids:
            exercise_row = {"eid": exercise_ids[exercise.name]}
        else:
            rows.append({"newExercise": exercise.name})
            exercise_row = {"newExercise": exercise.name}

        exercise_row["erows"] = [
            _set_line_to_erow(set_line)
            for set_line in exercise.sets
        ]
        did.append(exercise_row)

    rows.append({"on": day.date, "did": did})
    return rows


def _set_line_to_erow(set_line: ParsedSetLine) -> dict[str, Any]:
    reps_counts = Counter(set_line.reps)
    if len(reps_counts) != 1:
        return {
            "w": _weight_payload(set_line),
            "r": set_line.reps[0],
            "s": 1,
            "c": "Unconsolidated reps: " + ", ".join(str(rep) for rep in set_line.reps),
        }

    reps, sets = next(iter(reps_counts.items()))
    return {
        "w": _weight_payload(set_line),
        "r": reps,
        "s": sets,
    }


def _weight_payload(set_line: ParsedSetLine) -> dict[str, Any]:
    payload = {"v": set_line.weight_kg, "lb": 0}
    if set_line.uses_bodyweight:
        payload["usebw"] = 1
    return payload
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_weightxreps_jeditor.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/weightxreps tests/test_weightxreps_jeditor.py
git commit -m "feat(weightxreps): build jeditor rows"
```

---

### Task 6: Add OAuth PKCE Helpers and Token Store

**Files:**
- Create: `src/training_sync/config.py`
- Create: `src/training_sync/weightxreps/auth.py`
- Test: `tests/test_weightxreps_auth.py`

- [ ] **Step 1: Write failing OAuth tests**

Create `tests/test_weightxreps_auth.py`:

```python
from pathlib import Path

from training_sync.weightxreps.auth import (
    TokenSet,
    build_authorization_url,
    generate_pkce_pair,
    load_tokens,
    save_tokens,
)


def test_generate_pkce_pair_uses_short_verifier_and_s256_challenge():
    pair = generate_pkce_pair()

    assert 43 <= len(pair.code_verifier) <= 64
    assert pair.code_challenge
    assert pair.code_challenge_method == "S256"
    assert pair.code_challenge != pair.code_verifier


def test_build_authorization_url_contains_weightxreps_params():
    url = build_authorization_url(
        client_id="training-sync",
        redirect_uri="http://127.0.0.1:8765/callback",
        scope="jread,jwrite",
        state="state-123",
        code_challenge="challenge-123",
    )

    assert url.startswith("https://weightxreps.net/api/auth?")
    assert "client_id=training-sync" in url
    assert "redirect_uri=http%3A%2F%2F127.0.0.1%3A8765%2Fcallback" in url
    assert "scope=jread%2Cjwrite" in url
    assert "code_challenge=challenge-123" in url
    assert "code_challenge_method=S256" in url


def test_token_store_round_trips_json(tmp_path):
    path = tmp_path / "weightxreps-token.json"
    tokens = TokenSet(
        access_token="access",
        refresh_token="refresh",
        expires_in=3600,
        token_type="Bearer",
    )

    save_tokens(path, tokens)

    assert load_tokens(path) == tokens
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_weightxreps_auth.py -v
```

Expected: FAIL with missing functions.

- [ ] **Step 3: Implement OAuth helpers**

Create `src/training_sync/config.py`:

```python
"""Local configuration paths for training-sync."""

from pathlib import Path


def config_dir() -> Path:
    return Path.home() / ".config" / "training-sync"


def weightxreps_token_path() -> Path:
    return config_dir() / "weightxreps-token.json"
```

Create `src/training_sync/weightxreps/auth.py`:

```python
"""OAuth helpers for Weight x Reps."""

import base64
import hashlib
import json
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode

AUTH_ENDPOINT = "https://weightxreps.net/api/auth"


@dataclass(frozen=True)
class PkcePair:
    code_verifier: str
    code_challenge: str
    code_challenge_method: str = "S256"


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str | None
    expires_in: int | None
    token_type: str


def generate_pkce_pair() -> PkcePair:
    verifier = secrets.token_urlsafe(48)[:64]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return PkcePair(code_verifier=verifier, code_challenge=challenge)


def build_authorization_url(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
) -> str:
    query = urlencode(
        {
            "grant_type": "authorization_code",
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{AUTH_ENDPOINT}?{query}"


def save_tokens(path: Path, tokens: TokenSet) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(tokens), indent=2), encoding="utf-8")
    path.chmod(0o600)


def load_tokens(path: Path) -> TokenSet | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return TokenSet(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in"),
        token_type=data.get("token_type", "Bearer"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_weightxreps_auth.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/config.py src/training_sync/weightxreps/auth.py tests/test_weightxreps_auth.py
git commit -m "feat(weightxreps): add oauth pkce helpers"
```

---

### Task 7: Add Weight x Reps GraphQL Client

**Files:**
- Create: `src/training_sync/weightxreps/client.py`
- Test: `tests/test_weightxreps_client.py`

- [ ] **Step 1: Write failing client tests**

Create `tests/test_weightxreps_client.py`:

```python
from training_sync.weightxreps.client import WeightxRepsClient


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload=None):
        self.calls = []
        self.payload = payload or {"data": {"saveJEditor": True}}

    def post(self, url, json, headers):
        self.calls.append((url, json, headers))
        return FakeResponse(self.payload)


def test_graphql_posts_with_bearer_token():
    session = FakeSession()
    client = WeightxRepsClient(access_token="token-123", session=session)

    result = client.graphql("mutation X { x }", {"rows": []})

    assert result == {"saveJEditor": True}
    assert session.calls[0][0] == "https://weightxreps.net/api/graphql"
    assert session.calls[0][2]["Authorization"] == "Bearer token-123"


def test_save_jeditor_sends_rows_variable():
    session = FakeSession()
    client = WeightxRepsClient(access_token="token-123", session=session)

    client.save_jeditor([{"on": "2026-06-19", "did": []}])

    payload = session.calls[0][1]
    assert "saveJEditor" in payload["query"]
    assert payload["variables"] == {
        "rows": [{"on": "2026-06-19", "did": []}],
        "defaultDate": "2026-06-19",
    }


def test_jeditor_day_reads_existing_editor_data():
    session = FakeSession(
        {
            "data": {
                "jeditor": {
                    "baseBW": 71.4,
                    "did": [{"__typename": "JEditorDayTag", "on": "2026-06-19"}],
                    "exercises": [],
                }
            }
        }
    )
    client = WeightxRepsClient(access_token="token-123", session=session)

    data = client.jeditor_day("2026-06-19")

    assert data["baseBW"] == 71.4
    assert "jeditor" in session.calls[0][1]["query"]
    assert session.calls[0][1]["variables"] == {"ymd": "2026-06-19", "range": 0}


def test_day_has_content_uses_jeditor_data():
    session = FakeSession(
        {
            "data": {
                "jeditor": {
                    "baseBW": None,
                    "did": [{"__typename": "JEditorDayTag", "on": "2026-06-19"}],
                    "exercises": [],
                }
            }
        }
    )
    client = WeightxRepsClient(access_token="token-123", session=session)

    assert client.day_has_content("2026-06-19") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_weightxreps_client.py -v
```

Expected: FAIL with missing `WeightxRepsClient`.

- [ ] **Step 3: Implement GraphQL client**

Create `src/training_sync/weightxreps/client.py`:

```python
"""GraphQL client for Weight x Reps."""

from typing import Any

import requests

GRAPHQL_ENDPOINT = "https://weightxreps.net/api/graphql"

SAVE_JEDITOR_MUTATION = """
mutation SaveJEditor($rows: [JEditorSaveRow], $defaultDate: YMD!) {
  saveJEditor(rows: $rows, defaultDate: $defaultDate)
}
"""

JEDITOR_QUERY = """
query JEditorDay($ymd: YMD!, $range: Int) {
  jeditor(ymd: $ymd, range: $range) {
    baseBW
    exercises {
      e {
        id
        name
      }
    }
    did {
      __typename
      ... on JEditorDayTag {
        on
      }
      ... on JEditorBWTag {
        bw
      }
      ... on JEditorEBlock {
        e
        sets {
          v
          r
          s
          lb
          usebw
        }
      }
    }
  }
}
"""


class WeightxRepsClient:
    def __init__(self, access_token: str, session=None) -> None:
        self.access_token = access_token
        self.session = session or requests.Session()

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.post(
            GRAPHQL_ENDPOINT,
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(payload["errors"])
        return payload.get("data", {})

    def save_jeditor(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        default_date = _default_date_from_rows(rows)
        return self.graphql(
            SAVE_JEDITOR_MUTATION,
            {"rows": rows, "defaultDate": default_date},
        )

    def jeditor_day(self, date: str) -> dict[str, Any] | None:
        data = self.graphql(JEDITOR_QUERY, {"ymd": date, "range": 0})
        return data.get("jeditor")

    def day_has_content(self, date: str) -> bool:
        day = self.jeditor_day(date)
        if not day:
            return False
        return bool(day.get("did") or day.get("baseBW"))

    def verify_day(self, date: str, rows: list[dict[str, Any]]) -> bool:
        day = self.jeditor_day(date)
        return bool(day and day.get("did"))


def _default_date_from_rows(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        if row.get("on"):
            return row["on"]
    raise ValueError("JEditor rows must include an on date")
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_weightxreps_client.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/weightxreps/client.py tests/test_weightxreps_client.py
git commit -m "feat(weightxreps): add graphql client"
```

---

### Task 8: Add `weightxreps preview` CLI Command

**Files:**
- Modify: `src/training_sync/cli.py`
- Create: `src/training_sync/use_cases/__init__.py`
- Create: `src/training_sync/use_cases/weightxreps_preview.py`
- Test: `tests/test_training_sync_cli.py`
- Test: `tests/test_weightxreps_preview.py`

- [ ] **Step 1: Write failing preview tests**

Append to `tests/test_training_sync_cli.py`:

```python
def test_training_sync_weightxreps_preview_dispatches(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["training-sync", "weightxreps", "preview", "2026-06-19"])
    monkeypatch.setattr(
        cli,
        "preview_weightxreps_day",
        lambda date: calls.append(("preview", date)),
    )

    cli.main()

    assert calls == [("preview", "2026-06-19")]
```

Create `tests/test_weightxreps_preview.py`:

```python
from pathlib import Path

from training_sync.use_cases.weightxreps_preview import preview_weightxreps_day_from_vault


def test_preview_weightxreps_day_from_vault_builds_rows(tmp_path):
    vault = tmp_path / "vault"
    daily = vault / "daily/2026/06-June/2026-06-19-Friday.md"
    daily.parent.mkdir(parents=True)
    daily.write_text(
        """# Friday

## 🏃 Training
- Upper Body Day 2
```text
2026-06-19
@ 71.4 bw

#Chin Up
BW x 5, 5, 5
```

## 📚 Reading & Study
""",
        encoding="utf-8",
    )

    rows = preview_weightxreps_day_from_vault(
        vault,
        "2026-06-19",
        exercise_ids={"Chin Up": 10},
    )

    assert rows == [
        {"bw": 71.4, "lb": 0},
        {
            "on": "2026-06-19",
            "did": [
                {
                    "eid": 10,
                    "erows": [{"w": {"v": 0.0, "lb": 0, "usebw": 1}, "r": 5, "s": 3}],
                }
            ],
        },
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_training_sync_cli.py::test_training_sync_weightxreps_preview_dispatches tests/test_weightxreps_preview.py -v
```

Expected: FAIL with missing preview use case and CLI dispatch.

- [ ] **Step 3: Implement preview use case and CLI dispatch**

Create `src/training_sync/use_cases/__init__.py`:

```python
"""Use cases for training-sync."""
```

Create `src/training_sync/use_cases/weightxreps_preview.py`:

```python
"""Preview Weight x Reps rows from a vault daily note."""

from pathlib import Path
from typing import Any

from training_sync.renderers.weightxreps_text import parse_weightxreps_text
from training_sync.vault.daily import daily_note_path
from training_sync.vault.training_block import extract_training_section
from training_sync.weightxreps.jeditor import build_jeditor_rows


def preview_weightxreps_day_from_vault(
    vault_root: Path,
    date: str,
    exercise_ids: dict[str, int],
) -> list[dict[str, Any]]:
    note_path = daily_note_path(vault_root, date)
    if not note_path.exists():
        raise FileNotFoundError(f"Daily note not found: {note_path}")

    training_section = extract_training_section(note_path.read_text(encoding="utf-8"))
    text_block = _extract_first_text_block(training_section)
    parsed = parse_weightxreps_text(text_block)
    return build_jeditor_rows(parsed, exercise_ids)


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
```

Modify `src/training_sync/cli.py`:

```python
from pathlib import Path
import json

from training_sync.use_cases.weightxreps_preview import preview_weightxreps_day_from_vault

DEFAULT_VAULT_ROOT = Path("/Users/birrein/Library/Mobile Documents/iCloud~md~obsidian/Documents/brn-vault")
```

Add weightxreps subcommands in `main()`:

```python
weightxreps = subparsers.add_parser("weightxreps", help="Weight x Reps commands")
weightxreps_subparsers = weightxreps.add_subparsers(dest="weightxreps_command")

weightxreps_preview = weightxreps_subparsers.add_parser("preview", help="Preview Weight x Reps rows")
weightxreps_preview.add_argument("date")
```

Add dispatch before `parser.print_help()`:

```python
if args.command == "weightxreps" and args.weightxreps_command == "preview":
    preview_weightxreps_day(args.date)
    return
```

Add helper:

```python
def preview_weightxreps_day(date: str) -> None:
    rows = preview_weightxreps_day_from_vault(
        DEFAULT_VAULT_ROOT,
        date,
        exercise_ids={},
    )
    print(json.dumps(rows, ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_training_sync_cli.py tests/test_weightxreps_preview.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/cli.py src/training_sync/use_cases tests/test_training_sync_cli.py tests/test_weightxreps_preview.py
git commit -m "feat(weightxreps): preview vault day rows"
```

---

### Task 9: Add `weightxreps push` with Confirmation and Real Write

**Files:**
- Modify: `src/training_sync/cli.py`
- Create: `src/training_sync/use_cases/weightxreps_push.py`
- Test: `tests/test_weightxreps_push.py`

- [ ] **Step 1: Write failing push use-case tests**

Create `tests/test_weightxreps_push.py`:

```python
from pathlib import Path

import pytest

from training_sync.use_cases.weightxreps_push import push_weightxreps_day


class FakeWeightxRepsClient:
    def __init__(self, existing=False):
        self.existing = existing
        self.saved_rows = None

    def day_has_content(self, date):
        return self.existing

    def save_jeditor(self, rows):
        self.saved_rows = rows
        return {"saveJEditor": True}

    def verify_day(self, date, rows):
        return True


def _write_daily(vault: Path):
    daily = vault / "daily/2026/06-June/2026-06-19-Friday.md"
    daily.parent.mkdir(parents=True)
    daily.write_text(
        """# Friday

## 🏃 Training
- Upper Body Day 2
```text
2026-06-19
@ 71.4 bw

#Chin Up
BW x 5, 5, 5
```

## 📚 Reading & Study
""",
        encoding="utf-8",
    )


def test_push_weightxreps_day_writes_rows_when_remote_day_is_empty(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=False)

    result = push_weightxreps_day(
        vault,
        "2026-06-19",
        client,
        exercise_ids={"Chin Up": 10},
        yes=False,
    )

    assert result == "saved"
    assert client.saved_rows[0] == {"bw": 71.4, "lb": 0}


def test_push_weightxreps_day_requires_yes_when_remote_day_exists(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=True)

    with pytest.raises(RuntimeError, match="already has content"):
        push_weightxreps_day(
            vault,
            "2026-06-19",
            client,
            exercise_ids={"Chin Up": 10},
            yes=False,
        )


def test_push_weightxreps_day_replaces_existing_day_with_yes(tmp_path):
    vault = tmp_path / "vault"
    _write_daily(vault)
    client = FakeWeightxRepsClient(existing=True)

    result = push_weightxreps_day(
        vault,
        "2026-06-19",
        client,
        exercise_ids={"Chin Up": 10},
        yes=True,
    )

    assert result == "replaced"
    assert client.saved_rows is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_weightxreps_push.py -v
```

Expected: FAIL with missing `weightxreps_push`.

- [ ] **Step 3: Implement push use case**

Create `src/training_sync/use_cases/weightxreps_push.py`:

```python
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
    rows = preview_weightxreps_day_from_vault(vault_root, date, exercise_ids)
    exists = client.day_has_content(date)
    if exists and not yes:
        raise RuntimeError(f"Weight x Reps day {date} already has content; rerun with --yes to replace it")

    client.save_jeditor(rows)
    if not client.verify_day(date, rows):
        raise RuntimeError(f"Weight x Reps verification failed for {date}")

    return "replaced" if exists else "saved"
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_weightxreps_push.py tests/test_weightxreps_client.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/use_cases/weightxreps_push.py src/training_sync/weightxreps/client.py tests/test_weightxreps_push.py
git commit -m "feat(weightxreps): push vault day with verification"
```

---

### Task 10: Manual OAuth and Real Write Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Record confirmed Weight x Reps schema facts in README**

Add to `README.md` under the Weight x Reps section:

```markdown
Implementation notes:

- OAuth endpoint: `https://weightxreps.net/api/auth`
- GraphQL endpoint: `https://weightxreps.net/api/graphql`
- Required scopes: `jread,jwrite`
- Save mutation: `saveJEditor(rows: [JEditorSaveRow], defaultDate: YMD!)`
- Read-back query: `jeditor(ymd: YMD!, range: Int)`
```

- [ ] **Step 2: Run tests before manual auth**

Run:

```bash
python -m pytest
```

Expected: PASS.

- [ ] **Step 3: Authenticate against Weight x Reps**

Run:

```bash
training-sync weightxreps auth
```

Expected: browser opens Weight x Reps authorization, then token file is created at `~/.config/training-sync/weightxreps-token.json`.

- [ ] **Step 4: Preview one known training day**

Run:

```bash
training-sync weightxreps preview 2026-06-19
```

Expected: JSON rows include `{"bw": 71.4, "lb": 0}` and one day row where `on` is `"2026-06-19"` and `did` is a non-empty array.

- [ ] **Step 5: Perform one real write with explicit confirmation**

Run:

```bash
training-sync weightxreps push 2026-06-19 --yes
```

Expected: command reports `saved` or `replaced`, then read-back verification succeeds.

- [ ] **Step 6: Document auth and first real write**

Add to `README.md`:

```markdown
### Weight x Reps

Authenticate once:

```bash
training-sync weightxreps auth
```

Preview a day:

```bash
training-sync weightxreps preview 2026-06-19
```

Push a day, replacing existing Weight x Reps content only when confirmed:

```bash
training-sync weightxreps push 2026-06-19 --yes
```

Tokens are stored outside the repo under `~/.config/training-sync/`.
```

- [ ] **Step 7: Commit**

```bash
git add src/training_sync/weightxreps/client.py tests/test_weightxreps_client.py README.md
git commit -m "docs(weightxreps): document auth and push flow"
```

---

### Task 11: Add `sync DATE` Orchestration Skeleton

**Files:**
- Modify: `src/training_sync/cli.py`
- Create: `src/training_sync/use_cases/sync_day.py`
- Test: `tests/test_use_case_sync_day.py`

- [ ] **Step 1: Write failing sync use-case test**

Create `tests/test_use_case_sync_day.py`:

```python
from training_sync.use_cases.sync_day import sync_day


class FakeGarmin:
    def __init__(self):
        self.synced = []

    def sync_vault_day(self, date):
        self.synced.append(date)
        return "vault-updated"


class FakeWeightxReps:
    def __init__(self):
        self.pushed = []

    def push_day(self, date, yes):
        self.pushed.append((date, yes))
        return "replaced"


def test_sync_day_updates_vault_then_pushes_weightxreps():
    garmin = FakeGarmin()
    weightxreps = FakeWeightxReps()

    result = sync_day("2026-06-19", garmin=garmin, weightxreps=weightxreps)

    assert result == {
        "date": "2026-06-19",
        "vault": "vault-updated",
        "weightxreps": "replaced",
    }
    assert garmin.synced == ["2026-06-19"]
    assert weightxreps.pushed == [("2026-06-19", True)]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_use_case_sync_day.py -v
```

Expected: FAIL with missing `sync_day`.

- [ ] **Step 3: Implement sync skeleton**

Create `src/training_sync/use_cases/sync_day.py`:

```python
"""End-to-end one-day sync use case."""


def sync_day(date: str, garmin, weightxreps) -> dict[str, str]:
    vault_result = garmin.sync_vault_day(date)
    weightxreps_result = weightxreps.push_day(date, yes=True)
    return {
        "date": date,
        "vault": vault_result,
        "weightxreps": weightxreps_result,
    }
```

Add top-level `sync` parser in `src/training_sync/cli.py`:

```python
sync_parser = subparsers.add_parser("sync", help="Sync one date across Garmin, vault, and Weight x Reps")
sync_parser.add_argument("date")
```

Do not wire real adapters in this task. The goal is a tested orchestration seam.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_use_case_sync_day.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/cli.py src/training_sync/use_cases/sync_day.py tests/test_use_case_sync_day.py
git commit -m "feat(sync): add one-day sync orchestration"
```

---

## Final Verification

- [ ] **Run all tests**

```bash
python -m pytest
```

Expected: all tests pass.

- [ ] **Check CLI help**

```bash
training-sync --help
training-sync garmin --help
training-sync weightxreps --help
```

Expected: help text shows the new command groups.

- [ ] **Check legacy commands**

```bash
garmin-sync --fetch 2026-06-19
garmin-sync --weight 2026-06-19
```

Expected: both still work.

- [ ] **Check git status**

```bash
git status --short
```

Expected: clean after final commit.

## Self-Review Notes

- Spec coverage: CLI rename, compatibility aliases, vault parsing, Weight x Reps parsing, JEditor conversion, OAuth helpers, GraphQL client, preview, push, and sync skeleton are covered.
- Deferred by design: full MCP server, weekly sync, automatic daily creation, and direct image-to-Weight x Reps writes.
- Known risk: Task 10 must verify live Weight x Reps GraphQL names before real writes are trusted.
