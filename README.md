# Training Sync

A command-line tool to synchronize training data across Garmin Connect, Obsidian, and Weight x Reps.

Currently supports:
1. **Pushing** JSON strength training logs (like Fitbod exports) directly to Garmin Connect.
2. **Pulling (Fetching)** your Garmin activities (Running, Cycling, etc.) for a given date formatted for Markdown vaults (like Obsidian).
3. **Previewing and pushing** Weight x Reps training days from Obsidian daily notes.

## Installation

1. Clone this repository.
2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the package in editable mode (this installs dependencies and registers the CLI):
   ```bash
   pip install -e .
   ```

## Authentication

The first time you run the script, it will interactively ask for your Garmin Connect Email and Password in your terminal. 
It will then generate a session token file (`garmin_token.json`) locally. Future executions will reuse this token automatically.

> **Warning**: Ensure `garmin_token.json` is added to your `.gitignore`. Do not commit this file as it grants full access to your Garmin account!

## Usage

### 1. Pushing Strength Workouts to Garmin

You can sync a JSON payload either by passing the string directly or by providing a path to a JSON file.

**Using a File:**
```bash
training-sync garmin import-strength example_workout.json
```

**Using an Inline String:**
```bash
training-sync '{"date": "2026-06-15", "title": "Upper Body Day", "exercises": [{"name": "Barbell Bench Press", "sets": [{"reps": 10, "weight": 20}]}]}'
```

The script uses a massive dictionary (`garmin_exercises.json`) containing the exact Garmin Enum IDs to map your generic exercise names (e.g. "Barbell Bench Press") accurately to the Garmin platform. If a mapping is missing or incorrect, you can edit the `FITBOD_CUSTOM_MAP` inside `src/garmin_sync/mapper.py`.

### 2. Fetching Activities from Garmin

To download and format your activities for a specific date:

```bash
training-sync garmin fetch 2026-06-13
```

This will print out all activities recorded on that date in a clean Markdown format with the exact Garmin metrics (Pace, HR, Training Load, Cadence, Power, etc.), ready to be pasted into your daily notes.

For strength activities, the fetch output includes the closest Garmin weigh-in as a Weight x Reps body-weight tag when available:

```text
@ 71.4 bw
```

### 3. Fetching Body Weight from Garmin

To print only the closest Garmin body-weight tag for a specific date:

```bash
training-sync garmin weight 2026-06-19
```

This uses the nearest available Garmin weigh-in around the requested date and prints a Weight x Reps-compatible line.

### 4. Weight x Reps

Implementation notes:

- OAuth endpoint: `https://weightxreps.net/api/auth`
- GraphQL endpoint: `https://weightxreps.net/api/graphql`
- Required scopes: `jread,jwrite`
- Save mutation: `saveJEditor(rows: [JEditorSaveRow], defaultDate: YMD!)`
- Read-back query: `jeditor(ymd: YMD!, range: Int)`

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

Exercise aliases are also stored outside the repo:

```text
~/.config/training-sync/weightxreps-exercises.toml
```

Example:

```toml
[[exercises]]
weightxreps_name = "Barbell Hip Thrust"
weightxreps_id = 157721
aliases = [
  "Hip Thrust",
  "Barbell Hip Thrust with Bench",
]
```

Unknown exercises are not created automatically. If an exercise cannot be
resolved from the local mapping or the available Weight x Reps exercise IDs,
the command prints structured JSON with candidates and exits before writing.

Current limitation: Weight x Reps pushes only support standard `WEIGHT_X_REPS`
sets (`type: 0`). Time-based or distance-based exercise rows will need an
explicit set-type mapping before they are synced.

## License
MIT License
