# Garmin Sync Automation Design

## Context
Garmin Connect's React UI blocks programmatic form updates (like setting dropdown values) when using standard general-purpose browser agents. To ensure 100% reliable syncing of strength training data from Fitbod to Garmin Connect, we need a dedicated, native Playwright script that mimics human interaction.

## Architecture
- **Language**: Python 3
- **Library**: `playwright` (Python package)
- **Location**: `/Volumes/ssd1/dev/garmin-sync`
- **Execution Mode**: Local terminal execution, invoked silently by the AI agent.

## Authentication & Session Management
Playwright will use a dedicated persistent profile directory (`/Volumes/ssd1/dev/garmin-sync/profile`).
- On the **first run** (or if unauthenticated), the script can be configured to open Chrome visibly (`headless=False`) so the user can log in to Garmin.
- On **subsequent runs**, it will run silently (`headless=True`) using the saved session cookies, preventing interruptions to the user's workflow.

## Script Interface
The script (`sync.py`) will accept a single JSON string argument via the command line containing the exact workout data.
Example usage:
```bash
python3 sync.py '{"date": "2026-06-11", "title": "Upper Body Day 2", "exercises": [{"name": "Barbell Row", "sets": [{"reps": 8, "weight": 35}]}]}'
```

## Logic Flow
1. Parse the incoming JSON argument.
2. Launch Playwright with the persistent context.
3. Navigate to the Garmin Connect activities list.
4. Locate the specific Strength activity for the given `date`.
5. Enter "Edit" mode.
6. Update the title.
7. Manage rows:
   - Calculate needed rows vs. existing rows.
   - Delete excess rows or add missing rows to match exactly.
   - For each row: type the exercise `name`, wait for the React dropdown, and click the specific match.
   - Fill in the `reps` and `weight`.
8. Save the activity.
9. Exit.

## Updates to the AI Skill
The existing `garmin-obsidian-training-log` skill will be updated. The new step for Strength exercises will instruct the agent to:
1. Parse the Fitbod screenshots.
2. Map exercise names using the standard equivalents.
3. Construct the JSON string.
4. Execute the Python script locally.
5. Write the final formatted text block to Obsidian and `weightxreps`.
