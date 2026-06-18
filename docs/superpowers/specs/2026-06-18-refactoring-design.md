# Garmin Sync Modular Refactoring Design

## Context & Purpose
The `garmin-sync` project currently consists of a single 250-line script (`sync.py`) that handles CLI parsing, authentication, JSON mapping, and Garmin API interaction (both pushing strength sets and pulling running data). 

To make the codebase professional, maintainable, and suitable for open source, we will break down the monolith into a **Modular Pragmatic Architecture**.

## Architecture & Structure

The project will transition to an installable Python package layout.

```text
garmin-sync/
├── pyproject.toml                 # Package definition and dependencies
├── src/
│   └── garmin_sync/
│       ├── __init__.py            # Package root
│       ├── cli.py                 # Argparse definitions and CLI entrypoint
│       ├── auth.py                # Handles authentication and GarminSession wrapper
│       ├── mapper.py              # Dictionary loading and exercise aliases
│       └── commands/
│           ├── __init__.py
│           ├── push.py            # Logic to push Fitbod JSON to Garmin
│           └── fetch.py           # Logic to fetch activities and format as Markdown
```

## Component Details

### 1. `pyproject.toml`
Defines the package metadata and creates a command-line script entry point (`garmin-sync = garmin_sync.cli:main`). Dependencies (`garminconnect`) will be managed here, allowing users to run `pip install -e .`.

### 2. `auth.py`
Centralizes the Garmin API login logic. It will contain a `get_client()` function that:
- Checks if `garmin_token.json` exists in `~/.config/garmin-sync/` or the package directory.
- Falls back to interactive login if token is expired or missing.
- Provides a clear exception if run non-interactively without a valid token.

### 3. `mapper.py`
Separates the custom `FITBOD_CUSTOM_MAP` and the loading of `garmin_exercises.json`.
- Exposes a `get_mapping(fitbod_name: str) -> dict` function.

### 4. `commands/push.py`
Extracts the logic that calculates durations, assigns rest sets, and calls `set_activity_exercise_sets()`.

### 5. `commands/fetch.py`
Extracts the logic that queries activities by date, calculates pacing, and formats the output string as Obsidian-ready Markdown.

### 6. `cli.py`
Uses `argparse` to handle `--fetch` and `json_string`. Calls the respective functions in `push` or `fetch`.

## Error Handling & Logging
- Move away from print-based debugging for non-output logs. Use the standard `logging` library for warnings and informational messages. Standard output (`stdout`) will be reserved strictly for the generated Markdown or explicit user output.

## Scope Limits
- No external abstraction libraries or interfaces (No ABCs, no strict Clean Architecture).
- We maintain the exact same features without adding new business logic.

## Self Review
- Are there placeholders? No.
- Is internal consistency maintained? Yes.
- Is the scope focused? Yes, pure refactoring.
- Is it unambiguous? Yes, the target folder structure is clear.
