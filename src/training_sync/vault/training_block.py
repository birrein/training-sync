"""Read and update the ## 🏃 Training section in daily notes."""

import re

TRAINING_HEADING = "## 🏃 Training"


def extract_training_section(note_text: str) -> str:
    start, end = _section_bounds(note_text)
    return note_text[start:end].strip()


def training_section_has_content(note_text: str) -> bool:
    return bool(extract_training_section(note_text).strip())


def replace_training_section(note_text: str, new_content: str) -> str:
    start, end = _section_bounds(note_text)
    prefix = note_text[:start]
    suffix = note_text[end:]
    content = new_content.strip()
    return f"{prefix}{content}\n\n{suffix.lstrip()}"


def _section_bounds(note_text: str) -> tuple[int, int]:
    heading_match = re.search(
        rf"(?m)^{re.escape(TRAINING_HEADING)}$",
        note_text,
    )
    if heading_match is None:
        raise ValueError("Training section not found")

    content_start = heading_match.end()
    if note_text[content_start:content_start + 1] == "\n":
        content_start += 1

    next_heading = note_text.find("\n## ", content_start)
    if next_heading == -1:
        return content_start, len(note_text)

    return content_start, next_heading + 1
