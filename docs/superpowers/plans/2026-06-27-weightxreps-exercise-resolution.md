# Weight x Reps Exercise Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Weight x Reps exercise-resolution workflow so aliases resolve safely, unknown exercises stop before writing, and user decisions can be persisted outside the repository.

**Architecture:** Keep resolution separate from JEditor row construction. `exercise_mapping.py` owns TOML load/write/validation, `exercise_resolution.py` owns matching and structured unresolved output, `client.py` exposes the remote catalog, and CLI/use-case modules orchestrate without terminal-only prompts.

**Tech Stack:** Python 3.10+, pytest, stdlib `tomllib` with `tomli` fallback, local files under `~/.config/training-sync/`, Weight x Reps GraphQL.

---

## Current Status

The first safe slice was implemented in commit `fdeecf1 feat(weightxreps): require exercise resolution before push`.

- [x] Added `src/training_sync/weightxreps/exercise_mapping.py` with TOML load support.
- [x] Added `src/training_sync/weightxreps/exercise_resolution.py` with normalization, alias resolution, exact remote-name resolution, fuzzy candidate output, and structured `ExerciseResolutionRequired`.
- [x] Wired `src/training_sync/use_cases/weightxreps_preview.py` to resolve exercise IDs before calling `build_jeditor_rows`.
- [x] Wired `src/training_sync/use_cases/weightxreps_push.py` so unresolved exercises abort before `client.save_jeditor(rows)`.
- [x] Wired `src/training_sync/cli.py` to print resolution JSON and exit with code `2`.
- [x] Documented `~/.config/training-sync/weightxreps-exercises.toml` in `README.md`.
- [x] Covered the first slice with `tests/test_weightxreps_exercise_resolution.py`, `tests/test_weightxreps_preview.py`, `tests/test_weightxreps_push.py`, and `tests/test_training_sync_cli.py`.

Remaining tasks complete the original spec in smaller commits.

---

## File Structure

Create or extend these files:

- Modify: `src/training_sync/weightxreps/exercise_mapping.py`
  - Owns mapping dataclasses, TOML load/write, duplicate alias validation, backup creation, and deterministic serialization.
- Modify: `src/training_sync/weightxreps/exercise_resolution.py`
  - Owns resolution outcomes, local mapping checks, remote catalog checks, create-if-missing decisions, candidate scoring, and structured payloads.
- Modify: `src/training_sync/weightxreps/client.py`
  - Exposes a remote exercise catalog method used by resolver commands and push.
- Modify: `src/training_sync/use_cases/weightxreps_preview.py`
  - Loads a parsed vault day, resolves exercises, and returns either rows or structured unresolved output.
- Modify: `src/training_sync/use_cases/weightxreps_push.py`
  - Uses the same resolver path as preview and writes only after all exercises resolve or are explicitly allowed to create.
- Modify: `src/training_sync/cli.py`
  - Adds `training-sync weightxreps exercises resolve`, `map`, and `create` commands.
- Modify: `src/training_sync/config.py`
  - Already exposes `weightxreps_exercise_mapping_path`; tests should monkeypatch that function directly.
- Modify: `README.md`
  - Documents the command flow and mapping TOML decisions.

Tests:

- Extend: `tests/test_weightxreps_exercise_resolution.py`
- Extend: `tests/test_weightxreps_push.py`
- Extend: `tests/test_weightxreps_preview.py`
- Extend: `tests/test_training_sync_cli.py`
- Extend: `tests/test_weightxreps_client.py`
- Add: `tests/test_weightxreps_exercise_mapping.py`

---

### Task 1: Complete Mapping Validation

**Files:**
- Modify: `src/training_sync/weightxreps/exercise_mapping.py`
- Test: `tests/test_weightxreps_exercise_resolution.py` or `tests/test_weightxreps_exercise_mapping.py`

- [ ] **Step 1: Write failing tests for missing and duplicate mapping behavior**

Add tests:

```python
import pytest

from training_sync.weightxreps.exercise_mapping import (
    DuplicateExerciseAliasError,
    load_exercise_mappings,
)


def test_missing_exercise_mapping_file_loads_empty_list(tmp_path):
    assert load_exercise_mappings(tmp_path / "missing.toml") == []


def test_duplicate_alias_fails_with_both_targets(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"
    mapping_path.write_text(
        """[[exercises]]
weightxreps_name = "Barbell Hip Thrust"
weightxreps_id = 157721
aliases = ["Hip Thrust"]

[[exercises]]
weightxreps_name = "Hip Thrust Machine"
weightxreps_id = 157700
aliases = ["Hip Thrust"]
""",
        encoding="utf-8",
    )

    with pytest.raises(DuplicateExerciseAliasError) as exc:
        load_exercise_mappings(mapping_path)

    assert exc.value.alias == "hip thrust"
    assert exc.value.targets == ["Barbell Hip Thrust", "Hip Thrust Machine"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_weightxreps_exercise_resolution.py::test_missing_exercise_mapping_file_loads_empty_list tests/test_weightxreps_exercise_resolution.py::test_duplicate_alias_fails_with_both_targets -v
```

Expected: first test may already pass; duplicate test fails because `DuplicateExerciseAliasError` does not exist or duplicates are accepted.

- [ ] **Step 3: Implement duplicate validation**

Add to `src/training_sync/weightxreps/exercise_mapping.py`:

```python
class DuplicateExerciseAliasError(ValueError):
    def __init__(self, alias: str, targets: list[str]) -> None:
        self.alias = alias
        self.targets = targets
        super().__init__(
            f"Duplicate Weight x Reps exercise alias '{alias}' maps to: {', '.join(targets)}"
        )
```

After loading mappings, validate normalized aliases and canonical names. Reuse `normalize_exercise_name` carefully to avoid a circular import. If needed, move normalization into `exercise_mapping.py` and import it from `exercise_resolution.py`.

Implementation shape:

```python
def normalize_exercise_name(name: str) -> str:
    without_hash = name.strip().removeprefix("#").strip().lower()
    without_punctuation = re.sub(r"[^\w\s]", " ", without_hash)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def _validate_unique_aliases(mappings: list[ExerciseMapping]) -> None:
    seen: dict[str, str] = {}
    for mapping in mappings:
        for raw_name in [mapping.weightxreps_name, *mapping.aliases]:
            alias = normalize_exercise_name(raw_name)
            existing = seen.get(alias)
            if existing is not None and existing != mapping.weightxreps_name:
                raise DuplicateExerciseAliasError(alias, [existing, mapping.weightxreps_name])
            seen[alias] = mapping.weightxreps_name
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
pytest tests/test_weightxreps_exercise_resolution.py tests/test_weightxreps_preview.py tests/test_weightxreps_push.py -v
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/weightxreps/exercise_mapping.py src/training_sync/weightxreps/exercise_resolution.py tests/test_weightxreps_exercise_resolution.py
git commit -m "fix(weightxreps): validate duplicate exercise aliases"
```

---

### Task 2: Validate Mapped IDs Against Remote Catalog

**Files:**
- Modify: `src/training_sync/weightxreps/exercise_resolution.py`
- Test: `tests/test_weightxreps_exercise_resolution.py`

- [ ] **Step 1: Write failing tests for stale IDs and omitted IDs**

Add tests:

```python
import pytest

from training_sync.weightxreps.exercise_mapping import ExerciseMapping
from training_sync.weightxreps.exercise_resolution import ExerciseResolutionRequired, resolve_exercise_ids


def test_mapped_id_missing_from_remote_catalog_requires_refresh():
    mappings = [
        ExerciseMapping(
            weightxreps_name="Barbell Hip Thrust",
            weightxreps_id=157721,
            aliases=["Hip Thrust"],
        )
    ]

    with pytest.raises(ExerciseResolutionRequired) as exc:
        resolve_exercise_ids(
            date="2026-06-20",
            exercise_names=["Hip Thrust"],
            local_mappings=mappings,
            remote_exercise_ids={"Hip Thrust Machine": 157700},
        )

    payload = exc.value.payload()
    assert payload["unresolved"][0]["reason"] == "mapped_id_not_in_remote_catalog"


def test_mapping_without_id_resolves_by_canonical_remote_name():
    mappings = [
        ExerciseMapping(
            weightxreps_name="Barbell Hip Thrust",
            weightxreps_id=None,
            aliases=["Hip Thrust"],
        )
    ]

    resolved = resolve_exercise_ids(
        date="2026-06-20",
        exercise_names=["Hip Thrust"],
        local_mappings=mappings,
        remote_exercise_ids={"Barbell Hip Thrust": 157721},
    )

    assert resolved == {"Hip Thrust": 157721}
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_weightxreps_exercise_resolution.py::test_mapped_id_missing_from_remote_catalog_requires_refresh tests/test_weightxreps_exercise_resolution.py::test_mapping_without_id_resolves_by_canonical_remote_name -v
```

Expected: stale ID test fails because current resolver trusts any local ID.

- [ ] **Step 3: Implement remote ID validation**

In `resolve_exercise_ids`, build a set of remote IDs:

```python
remote_ids = set(remote_exercise_ids.values())
```

When a mapping has `weightxreps_id`, resolve only if `mapping.weightxreps_id in remote_ids`. If not, append `UnresolvedExercise` with reason `mapped_id_not_in_remote_catalog` and candidates from `_candidate_matches`.

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
pytest tests/test_weightxreps_exercise_resolution.py -v
```

Expected: all resolver tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/weightxreps/exercise_resolution.py tests/test_weightxreps_exercise_resolution.py
git commit -m "fix(weightxreps): reject stale mapped exercise ids"
```

---

### Task 3: Add Controlled `create_if_missing`

**Files:**
- Modify: `src/training_sync/weightxreps/exercise_mapping.py`
- Modify: `src/training_sync/weightxreps/exercise_resolution.py`
- Modify: `src/training_sync/weightxreps/jeditor.py`
- Test: `tests/test_weightxreps_exercise_resolution.py`
- Test: `tests/test_weightxreps_jeditor.py`

- [ ] **Step 1: Write failing tests for explicit creation**

Add tests:

```python
from training_sync.weightxreps.exercise_mapping import ExerciseMapping
from training_sync.weightxreps.exercise_resolution import resolve_exercise_ids


def test_create_if_missing_returns_new_exercise_marker():
    mappings = [
        ExerciseMapping(
            weightxreps_name="New Exercise Name",
            weightxreps_id=None,
            aliases=["New Exercise Name"],
            create_if_missing=True,
        )
    ]

    resolved = resolve_exercise_ids(
        date="2026-06-20",
        exercise_names=["New Exercise Name"],
        local_mappings=mappings,
        remote_exercise_ids={},
    )

    assert resolved == {"New Exercise Name": None}
```

If the existing `build_jeditor_rows(day, exercise_ids)` cannot represent controlled creation cleanly, change the expected type to a small dataclass such as:

```python
@dataclass(frozen=True)
class ResolvedExercise:
    exercise_id: int | None
    create_if_missing: bool = False
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_weightxreps_exercise_resolution.py::test_create_if_missing_returns_new_exercise_marker -v
```

Expected: fails because `ExerciseMapping` does not support `create_if_missing`.

- [ ] **Step 3: Implement mapping field and resolver behavior**

Update dataclass:

```python
@dataclass(frozen=True)
class ExerciseMapping:
    weightxreps_name: str
    weightxreps_id: int | None
    aliases: list[str]
    create_if_missing: bool = False
```

Load with:

```python
create_if_missing=bool(exercise.get("create_if_missing", False))
```

Resolver rule:

```python
if mapping.create_if_missing:
    resolved[exercise_name] = None
    continue
```

Then adapt row building so only explicitly allowed `None` emits `newExercise`. Do not reintroduce accidental `newExercise` for unmapped exercises.

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
pytest tests/test_weightxreps_exercise_resolution.py tests/test_weightxreps_jeditor.py tests/test_weightxreps_push.py -v
```

Expected: controlled create passes; unresolved exercises still abort before write.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/weightxreps/exercise_mapping.py src/training_sync/weightxreps/exercise_resolution.py src/training_sync/weightxreps/jeditor.py tests/test_weightxreps_exercise_resolution.py tests/test_weightxreps_jeditor.py tests/test_weightxreps_push.py
git commit -m "feat(weightxreps): allow explicit new exercise mappings"
```

---

### Task 4: Add Mapping Write Helpers With Backups

**Files:**
- Modify: `src/training_sync/weightxreps/exercise_mapping.py`
- Test: `tests/test_weightxreps_exercise_mapping.py`

- [ ] **Step 1: Write failing tests for deterministic TOML writes and backups**

Add tests:

```python
from training_sync.weightxreps.exercise_mapping import (
    ExerciseMapping,
    add_alias_mapping,
    load_exercise_mappings,
)


def test_add_alias_mapping_writes_deterministic_toml(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"

    add_alias_mapping(
        mapping_path,
        incoming_name="Barbell Hip Thrust with Bench",
        weightxreps_name="Barbell Hip Thrust",
        weightxreps_id=157721,
    )

    assert mapping_path.read_text(encoding="utf-8") == (
        '[[exercises]]\n'
        'weightxreps_name = "Barbell Hip Thrust"\n'
        'weightxreps_id = 157721\n'
        'aliases = [\n'
        '  "Barbell Hip Thrust",\n'
        '  "Barbell Hip Thrust with Bench",\n'
        ']\n'
    )
    assert load_exercise_mappings(mapping_path) == [
        ExerciseMapping(
            weightxreps_name="Barbell Hip Thrust",
            weightxreps_id=157721,
            aliases=["Barbell Hip Thrust", "Barbell Hip Thrust with Bench"],
        )
    ]


def test_add_alias_mapping_creates_backup_before_overwrite(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"
    mapping_path.write_text(
        '[[exercises]]\nweightxreps_name = "Chin Up"\nweightxreps_id = 10\naliases = ["Chin Up"]\n',
        encoding="utf-8",
    )

    add_alias_mapping(
        mapping_path,
        incoming_name="Pull Up",
        weightxreps_name="Chin Up",
        weightxreps_id=10,
    )

    backups = list(tmp_path.glob("weightxreps-exercises.toml.*.bak"))
    assert len(backups) == 1
    assert 'weightxreps_name = "Chin Up"' in backups[0].read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_weightxreps_exercise_mapping.py -v
```

Expected: fails because `add_alias_mapping` does not exist.

- [ ] **Step 3: Implement deterministic writer**

Implement:

```python
def add_alias_mapping(
    path: Path,
    incoming_name: str,
    weightxreps_name: str,
    weightxreps_id: int,
) -> None:
    mappings = load_exercise_mappings(path)
    updated = _merge_alias(mappings, incoming_name, weightxreps_name, weightxreps_id)
    _backup_if_exists(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_exercise_mappings(updated), encoding="utf-8")
    path.chmod(0o600)
```

Use only deterministic ordering:

```python
def _sorted_unique(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(values), key=str.casefold)
```

Do not add a TOML writer dependency in this task; use deterministic string serialization for the schema shown in the tests.

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
pytest tests/test_weightxreps_exercise_mapping.py tests/test_weightxreps_exercise_resolution.py -v
```

Expected: mapping write tests pass and duplicate validation still passes.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/weightxreps/exercise_mapping.py tests/test_weightxreps_exercise_mapping.py
git commit -m "feat(weightxreps): persist exercise alias mappings"
```

---

### Task 5: Add CLI `exercises map` Command

**Files:**
- Modify: `src/training_sync/cli.py`
- Test: `tests/test_training_sync_cli.py`

- [ ] **Step 1: Write failing CLI dispatch test**

Add test:

```python
def test_training_sync_weightxreps_exercises_map_dispatches(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "weightxreps_exercise_mapping_path", lambda: tmp_path / "map.toml")
    monkeypatch.setattr(
        cli,
        "add_alias_mapping",
        lambda path, incoming_name, weightxreps_name, weightxreps_id: calls.append(
            (path, incoming_name, weightxreps_name, weightxreps_id)
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "training-sync",
            "weightxreps",
            "exercises",
            "map",
            "--incoming",
            "Barbell Hip Thrust with Bench",
            "--existing-name",
            "Barbell Hip Thrust",
            "--existing-id",
            "157721",
        ],
    )

    cli.main()

    assert calls == [
        (
            tmp_path / "map.toml",
            "Barbell Hip Thrust with Bench",
            "Barbell Hip Thrust",
            157721,
        )
    ]
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_training_sync_cli.py::test_training_sync_weightxreps_exercises_map_dispatches -v
```

Expected: argparse rejects `exercises`.

- [ ] **Step 3: Implement parser and dispatch**

Add parser:

```python
weightxreps_exercises = weightxreps_subparsers.add_parser("exercises", help="Manage Weight x Reps exercise mappings")
weightxreps_exercise_subparsers = weightxreps_exercises.add_subparsers(dest="weightxreps_exercise_command")

weightxreps_map = weightxreps_exercise_subparsers.add_parser("map", help="Map an incoming exercise to an existing Weight x Reps exercise")
weightxreps_map.add_argument("--incoming", required=True)
weightxreps_map.add_argument("--existing-name", required=True)
weightxreps_map.add_argument("--existing-id", required=True, type=int)
```

Add dispatch:

```python
if (
    getattr(args, "command", None) == "weightxreps"
    and args.weightxreps_command == "exercises"
    and args.weightxreps_exercise_command == "map"
):
    add_alias_mapping(
        weightxreps_exercise_mapping_path(),
        incoming_name=args.incoming,
        weightxreps_name=args.existing_name,
        weightxreps_id=args.existing_id,
    )
    print("mapped")
    return
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
pytest tests/test_training_sync_cli.py::test_training_sync_weightxreps_exercises_map_dispatches -v
```

Expected: test passes.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/cli.py tests/test_training_sync_cli.py
git commit -m "feat(weightxreps): add exercise map command"
```

---

### Task 6: Add CLI `exercises create` Command

**Files:**
- Modify: `src/training_sync/weightxreps/exercise_mapping.py`
- Modify: `src/training_sync/cli.py`
- Test: `tests/test_weightxreps_exercise_mapping.py`
- Test: `tests/test_training_sync_cli.py`

- [ ] **Step 1: Write failing tests for create command**

Add mapping test:

```python
from training_sync.weightxreps.exercise_mapping import add_create_mapping


def test_add_create_mapping_marks_exercise_as_create_if_missing(tmp_path):
    mapping_path = tmp_path / "weightxreps-exercises.toml"

    add_create_mapping(mapping_path, incoming_name="New Exercise Name")

    assert mapping_path.read_text(encoding="utf-8") == (
        '[[exercises]]\n'
        'weightxreps_name = "New Exercise Name"\n'
        'create_if_missing = true\n'
        'aliases = [\n'
        '  "New Exercise Name",\n'
        ']\n'
    )
```

Add CLI test:

```python
def test_training_sync_weightxreps_exercises_create_dispatches(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "weightxreps_exercise_mapping_path", lambda: tmp_path / "map.toml")
    monkeypatch.setattr(
        cli,
        "add_create_mapping",
        lambda path, incoming_name: calls.append((path, incoming_name)),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "training-sync",
            "weightxreps",
            "exercises",
            "create",
            "--incoming",
            "New Exercise Name",
        ],
    )

    cli.main()

    assert calls == [(tmp_path / "map.toml", "New Exercise Name")]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_weightxreps_exercise_mapping.py::test_add_create_mapping_marks_exercise_as_create_if_missing tests/test_training_sync_cli.py::test_training_sync_weightxreps_exercises_create_dispatches -v
```

Expected: both tests fail because helpers and parser command do not exist.

- [ ] **Step 3: Implement create helper and command**

Add:

```python
def add_create_mapping(path: Path, incoming_name: str) -> None:
    mappings = load_exercise_mappings(path)
    updated = [
        *mappings,
        ExerciseMapping(
            weightxreps_name=incoming_name,
            weightxreps_id=None,
            aliases=[incoming_name],
            create_if_missing=True,
        ),
    ]
    _backup_if_exists(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_exercise_mappings(updated), encoding="utf-8")
    path.chmod(0o600)
```

Add argparse command:

```python
weightxreps_create = weightxreps_exercise_subparsers.add_parser("create", help="Allow creating a new Weight x Reps exercise")
weightxreps_create.add_argument("--incoming", required=True)
```

Dispatch to `add_create_mapping`.

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
pytest tests/test_weightxreps_exercise_mapping.py tests/test_training_sync_cli.py -v
```

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/weightxreps/exercise_mapping.py src/training_sync/cli.py tests/test_weightxreps_exercise_mapping.py tests/test_training_sync_cli.py
git commit -m "feat(weightxreps): add exercise create command"
```

---

### Task 7: Add CLI `exercises resolve` Command

**Files:**
- Modify: `src/training_sync/cli.py`
- Test: `tests/test_training_sync_cli.py`

- [ ] **Step 1: Write failing test for resolve command JSON**

Add test:

```python
def test_training_sync_weightxreps_exercises_resolve_prints_resolution_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "DEFAULT_VAULT_ROOT", tmp_path / "vault")
    monkeypatch.setattr(cli, "weightxreps_exercise_mapping_path", lambda: tmp_path / "map.toml")
    monkeypatch.setattr(cli, "load_exercise_mappings", lambda path: [])
    monkeypatch.setattr(
        cli,
        "preview_weightxreps_day_from_vault",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ExerciseResolutionRequired(
                "2026-06-20",
                [
                    UnresolvedExercise(
                        incoming_exercise="Hip Thrust",
                        normalized_name="hip thrust",
                        reason="no_local_mapping",
                        candidates=[],
                    )
                ],
            )
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["training-sync", "weightxreps", "exercises", "resolve", "2026-06-20"],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 2
    assert '"status": "exercise_resolution_required"' in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_training_sync_cli.py::test_training_sync_weightxreps_exercises_resolve_prints_resolution_json -v
```

Expected: argparse rejects `resolve`.

- [ ] **Step 3: Implement resolve command**

Add parser:

```python
weightxreps_resolve = weightxreps_exercise_subparsers.add_parser("resolve", help="Resolve exercise mappings for a vault date")
weightxreps_resolve.add_argument("date")
```

Dispatch:

```python
if (
    getattr(args, "command", None) == "weightxreps"
    and args.weightxreps_command == "exercises"
    and args.weightxreps_exercise_command == "resolve"
):
    preview_weightxreps_day(args.date)
    return
```

This command uses the same preview resolver behavior and JSON output. Later catalog-auth changes belong to Task 8.

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
pytest tests/test_training_sync_cli.py::test_training_sync_weightxreps_exercises_resolve_prints_resolution_json -v
```

Expected: test passes.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/cli.py tests/test_training_sync_cli.py
git commit -m "feat(weightxreps): add exercise resolve command"
```

---

### Task 8: Expose Remote Exercise Catalog

**Files:**
- Modify: `src/training_sync/weightxreps/client.py`
- Modify: `src/training_sync/use_cases/weightxreps_push.py`
- Test: `tests/test_weightxreps_client.py`
- Test: `tests/test_weightxreps_push.py`

- [ ] **Step 1: Write failing client test**

Add test:

```python
def test_exercise_catalog_reads_remote_exercise_names():
    session = FakeSession(
        {
            "data": {
                "getExercises": [
                    {"id": "157721", "name": "Barbell Hip Thrust"},
                    {"id": "158078", "name": "Hanging Knee Raise"},
                ]
            }
        }
    )
    client = WeightxRepsClient(access_token="token-123", session=session)

    catalog = client.exercise_catalog(user_id=12345)

    assert catalog == {
        "Barbell Hip Thrust": 157721,
        "Hanging Knee Raise": 158078,
    }
    assert "getExercises" in session.calls[0][1]["query"]
    assert session.calls[0][1]["variables"] == {"uid": 12345}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_weightxreps_client.py::test_exercise_catalog_reads_remote_exercise_names -v
```

Expected: fails because `exercise_catalog` does not exist.

- [ ] **Step 3: Implement GraphQL catalog method**

Add query:

```python
EXERCISE_CATALOG_QUERY = """
query ExerciseCatalog($uid: Int!) {
  getExercises(uid: $uid) {
    id
    name
  }
}
"""
```

Add method:

```python
def exercise_catalog(self, user_id: int) -> dict[str, int]:
    data = self.graphql(EXERCISE_CATALOG_QUERY, {"uid": user_id})
    return {
        exercise["name"]: int(exercise["id"])
        for exercise in data.get("getExercises") or []
        if exercise.get("name") and exercise.get("id")
    }
```

- [ ] **Step 4: Use catalog when available**

In `push_weightxreps_day`, prefer explicit `exercise_ids`, then `client.exercise_catalog(user_id)` once config has `user_id`, then current `client.exercise_ids(date)` fallback.

If user ID is not yet configured, keep `exercise_ids(date)` as partial catalog and include catalog source in structured output in Task 9.

- [ ] **Step 5: Run tests to verify pass**

Run:

```bash
pytest tests/test_weightxreps_client.py tests/test_weightxreps_push.py -v
```

Expected: tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/training_sync/weightxreps/client.py src/training_sync/use_cases/weightxreps_push.py tests/test_weightxreps_client.py tests/test_weightxreps_push.py
git commit -m "feat(weightxreps): expose exercise catalog"
```

---

### Task 9: Add Catalog Source to Structured Output

**Files:**
- Modify: `src/training_sync/weightxreps/exercise_resolution.py`
- Modify: `src/training_sync/use_cases/weightxreps_preview.py`
- Modify: `src/training_sync/use_cases/weightxreps_push.py`
- Test: `tests/test_weightxreps_exercise_resolution.py`

- [ ] **Step 1: Write failing payload test**

Add test:

```python
def test_resolution_payload_includes_catalog_source():
    with pytest.raises(ExerciseResolutionRequired) as exc:
        resolve_exercise_ids(
            date="2026-06-20",
            exercise_names=["Unknown Lift"],
            local_mappings=[],
            remote_exercise_ids={},
            catalog_source="partial_jeditor",
        )

    assert exc.value.payload()["catalog_source"] == "partial_jeditor"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_weightxreps_exercise_resolution.py::test_resolution_payload_includes_catalog_source -v
```

Expected: fails because resolver does not accept `catalog_source`.

- [ ] **Step 3: Implement catalog source field**

Update function signature:

```python
def resolve_exercise_ids(
    date: str,
    exercise_names: list[str],
    local_mappings: list[ExerciseMapping],
    remote_exercise_ids: dict[str, int],
    catalog_source: str = "unknown",
) -> dict[str, int]:
```

Update exception:

```python
class ExerciseResolutionRequired(RuntimeError):
    def __init__(self, date: str, unresolved: list[UnresolvedExercise], catalog_source: str) -> None:
        self.catalog_source = catalog_source
```

Payload includes:

```python
"catalog_source": self.catalog_source
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
pytest tests/test_weightxreps_exercise_resolution.py tests/test_weightxreps_preview.py tests/test_weightxreps_push.py -v
```

Expected: all selected tests pass after updating existing expected payloads.

- [ ] **Step 5: Commit**

```bash
git add src/training_sync/weightxreps/exercise_resolution.py src/training_sync/use_cases/weightxreps_preview.py src/training_sync/use_cases/weightxreps_push.py tests/test_weightxreps_exercise_resolution.py tests/test_weightxreps_preview.py tests/test_weightxreps_push.py
git commit -m "feat(weightxreps): report exercise catalog source"
```

---

### Task 10: Update README With Full Agent Flow

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add command documentation**

Add this under the Weight x Reps section:

```markdown
Resolve a day before pushing:

```bash
training-sync weightxreps exercises resolve 2026-06-20
```

Map an incoming exercise to an existing Weight x Reps exercise:

```bash
training-sync weightxreps exercises map \
  --incoming "Barbell Hip Thrust with Bench" \
  --existing-name "Barbell Hip Thrust" \
  --existing-id 157721
```

Allow creating a new exercise only when it is intentional:

```bash
training-sync weightxreps exercises create \
  --incoming "New Exercise Name"
```
```

- [ ] **Step 2: Run README grep check**

Run:

```bash
rg -n "weightxreps exercises (resolve|map|create)|create_if_missing|weightxreps-exercises.toml" README.md
```

Expected: all three commands and the mapping file are documented.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(weightxreps): document exercise resolution commands"
```

---

### Task 11: Final Verification

**Files:**
- All changed files from previous tasks.

- [ ] **Step 1: Run focused Weight x Reps tests**

Run:

```bash
pytest tests/test_weightxreps_exercise_resolution.py tests/test_weightxreps_exercise_mapping.py tests/test_weightxreps_client.py tests/test_weightxreps_preview.py tests/test_weightxreps_push.py tests/test_training_sync_cli.py -v
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest
```

Expected: all tests pass.

- [ ] **Step 3: Check whitespace**

Run:

```bash
git diff --check
```

Expected: no output and exit code `0`.

- [ ] **Step 4: Manual dry run for unresolved exercise**

Run against a date with one intentionally unmapped exercise:

```bash
training-sync weightxreps exercises resolve 2026-06-20
```

Expected: command exits with code `2`, prints JSON with `status`, `date`, `unresolved`, `candidates`, `allowed_actions`, `suggested_agent_question`, and does not write to Weight x Reps.

- [ ] **Step 5: Manual mapped push**

After adding a mapping:

```bash
training-sync weightxreps push 2026-06-20 --yes
```

Expected: command writes to existing Weight x Reps exercise IDs and verifies the saved day.

- [ ] **Step 6: Commit final verification fixes**

If final verification changes any implementation, stage the exact files changed by the verification fixes. For example, if the fixes touched resolver output and CLI docs:

```bash
git add src/training_sync/weightxreps/exercise_resolution.py README.md
git commit -m "fix(weightxreps): complete exercise resolution flow"
```

---

## Spec Coverage Review

- Durable local mapping: partially done; completed by Tasks 1, 4, 5, and 6.
- Resolve before JEditor rows: done in commit `fdeecf1`; refined by Tasks 2, 3, and 9.
- Avoid accidental new exercises: done for unmapped exercises; completed for explicit creation by Task 3.
- Machine-readable unresolved output: done in commit `fdeecf1`; catalog source added by Task 9.
- Agent decision persistence: completed by Tasks 4, 5, and 6.
- Remote catalog source: completed by Task 8, with catalog source reporting in Task 9.
- Error handling: duplicate aliases in Task 1, stale IDs in Task 2, invalid TOML should use the existing TOML parser exception with file path in CLI output if surfaced by commands.
- Testing strategy: completed across Tasks 1 through 11.

## Execution Choice

Plan complete and saved to `docs/superpowers/plans/2026-06-27-weightxreps-exercise-resolution.md`.

Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - execute tasks in this session using executing-plans, batch execution with checkpoints.
