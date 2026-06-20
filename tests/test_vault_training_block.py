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
