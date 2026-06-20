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
