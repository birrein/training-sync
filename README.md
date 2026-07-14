# Training Sync

A command-line tool to synchronize training data across Garmin Connect, Obsidian, and Weight x Reps.

Currently supports:
1. **Pushing** JSON strength training logs (like Fitbod exports) directly to Garmin Connect.
2. **Pulling (Fetching)** your Garmin activities (Running, Cycling, etc.) for a given date formatted for Markdown vaults (like Obsidian).
3. **Previewing and pushing** Weight x Reps training days from Obsidian daily notes.
4. **Reconciling one complete day** from Garmin into an existing Obsidian daily note and Weight x Reps.

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

The first time you run a Garmin command, it will interactively ask for your Garmin Connect email and password in your terminal.
It will then generate a session token file outside the repo:

```text
~/.config/training-sync/garmin-token.json
```

Future executions reuse this token automatically.

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

### 4. Reconciling a Day Across All Services

To fetch every Garmin activity for a date, update its existing Obsidian daily
note, and replace the corresponding Weight x Reps day with one reconciled
full-day payload:

```bash
training-sync sync YYYY-MM-DD [--yes]
```

The daily note must already exist and contain the exact `## 🏃 Training`
heading; the command never creates the daily note or that heading. It performs
its complete preflight before writing: it fetches all activities for the date,
resolves Weight x Reps exercise IDs, and builds both the updated daily and
remote payload. If either the daily training section or the Weight x Reps day
already has content, omit `--yes` to stop safely; pass `--yes` as the single
shared confirmation to replace the daily training section and the complete
remote day.

All Garmin activities are written to the daily in chronological order. For
Weight x Reps, the reconciled full day preserves the existing body weight and
strength exercises, removes previously generated cardio rows, and creates one
new structured row for each supported Garmin running or cycling activity:

- `type: 1` stores duration-only cardio.
- `type: 2` stores duration plus distance, including the distance value and
  unit. Running maps to `Running`; cycling and virtual rides map to `Cycling`.

After updating the daily, the command saves the complete Weight x Reps day and
verifies it with a read-back. If the remote save or read-back fails, the updated
daily is intentionally retained so a retry can rebuild the same full-day
payload; the command reports the daily path and the Weight x Reps failure as a
partial sync. Review that error before retrying. The integrated sync does not
create unknown Weight x Reps exercises automatically: unresolved mappings stop
the preflight before either destination is changed.

### 5. Weight x Reps

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

When pushing a day that intentionally creates new exercises, provide your
Weight x Reps user id so the command can load the full exercise catalog before
writing:

```bash
training-sync weightxreps push 2026-06-19 --yes --user-id 12345
```

You can also set it once outside the repo:

```bash
export WEIGHTXREPS_USER_ID=12345
```

or store only the numeric id in:

```text
~/.config/training-sync/weightxreps-user-id
```

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

To intentionally allow a new Weight x Reps exercise to be created when no
existing exercise matches, mark that mapping explicitly:

```toml
[[exercises]]
weightxreps_name = "New Exercise Name"
aliases = ["New Exercise Name"]
create_if_missing = true
```

Unknown exercises are not created automatically. If an exercise cannot be
resolved from the local mapping or the available Weight x Reps exercise IDs,
the command prints structured JSON with candidates and exits before writing.
Mappings with `create_if_missing = true` still require the full catalog from a
configured user id; without one, pushes keep using the safe partial JEditor
catalog and reject creation before writing.

## License
MIT License
