from pathlib import Path

import pytest

from training_sync.vault.daily import daily_note_path
from training_sync.vault.training_block import (
    extract_training_section,
    replace_training_section,
    training_section_has_content,
)


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


@pytest.mark.parametrize("content", ["", "\n", "  \n\t"])
def test_training_section_has_content_treats_whitespace_as_empty(content):
    note = f"# Friday\n\n## 🏃 Training\n{content}\n## 📚 Reading & Study\n"

    assert training_section_has_content(note) is False


def test_training_section_has_content_accepts_any_non_whitespace_content():
    note = "# Friday\n\n## 🏃 Training\n  - Activity  \n\n## 📚 Reading & Study\n"

    assert training_section_has_content(note) is True


def test_replace_training_section_preserves_exact_surrounding_sections():
    note = "# Friday\n\n## ✅ Tasks\n- Keep me\n\n## 🏃 Training\nOld\n\n## 📚 Reading & Study\n- Keep me too\n"

    updated = replace_training_section(note, "- New Activity")

    assert updated.startswith("# Friday\n\n## ✅ Tasks\n- Keep me\n\n## 🏃 Training\n")
    assert updated.endswith("## 📚 Reading & Study\n- Keep me too\n")
    assert "Old" not in updated


def test_replace_training_section_requires_existing_heading():
    with pytest.raises(ValueError, match="Training section not found"):
        replace_training_section("# Friday\n", "- Activity")


@pytest.mark.parametrize("near_miss", ["## 🏃 Training Plan", "## 🏃 Training extra", "### 🏃 Training"])
def test_training_section_requires_exact_heading_line(near_miss):
    note = f"# Friday\n\n{near_miss}\nOld\n\n## 📚 Reading & Study\n"

    with pytest.raises(ValueError, match="Training section not found"):
        extract_training_section(note)
