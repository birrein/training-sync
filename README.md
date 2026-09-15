# Training Sync

A command-line tool to synchronize training data across Garmin Connect, Obsidian, and Weight x Reps.

Currently supports:
1. **Pushing** JSON strength training logs (like Fitbod exports) directly to Garmin Connect.
2. **Pulling (Fetching)** your Garmin activities (Running, Cycling, etc.) for a given date formatted for Markdown vaults (like Obsidian).
3. **Previewing and pushing** Weight x Reps training days from Obsidian daily notes.
4. **Reconciling one complete day** from Garmin into an existing Obsidian daily note and Weight x Reps.
5. **Preparing, verifying, and scheduling** Garmin planned strength, cycling,
   and running workouts from source-independent JSON.
6. **Reading and explicitly managing** Intervals.icu activity replicas.

## Canonical activity safety

Garmin is authoritative for verified objective completed activity data. The vault
keeps subjective context (including RIR, global RPE, Feel, and recovery), while
Weight x Reps is the structured strength destination. A Fitbod screenshot is
only an import input: it is not a completed activity until Garmin has accepted
it and a Garmin read-back verifies the expected workout.

Targets are always explicit. The existing `training-sync sync DATE` command
continues to affect only the vault and Weight x Reps; configuring Intervals.icu
never adds it implicitly. New lifecycle commands preview first and require
`--yes` to apply the exact displayed provider-local operation. A failed target
is reported independently; verified targets are not rolled back.

## Installation

1. Clone this repository.
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for your
   platform and verify the installation:
   ```bash
   uv --version
   ```
3. Synchronize the project environment, including development tools:
   ```bash
   uv sync --dev
   ```

The project keeps standard PEP 621 metadata and the setuptools build backend,
so pip installation remains technically supported. The development workflow
uses uv and the committed `uv.lock` for reproducible dependency resolution.

### Direct operational CLI

For normal operational use, install the CLI once as a persistent, non-editable
uv tool from the checkout you want to use as its source:

```bash
uv tool install /path/to/training-sync
uv tool update-shell
```

`uv tool update-shell` helps add uv's tool executable directory to your PATH;
run it only when needed for your shell. After that, invoke the CLI directly
from any checkout or working directory:

```bash
training-sync --help
training-sync --version
training-sync sync YYYY-MM-DD
```

This project change does not install a tool or modify your shell. The
non-editable install is the portable default because it copies/builds the
package into uv's isolated tool environment instead of binding the executable
to one checkout.

To make another local checkout the source of the direct command, explicitly
reinstall it:

```bash
uv tool install --force /path/to/training-sync
```

`uv tool upgrade training-sync` refreshes the tool's recorded source; it does
not select an arbitrary different checkout. Use `--force` with the desired
checkout when switching sources. `uv tool install --editable` is available for
local development, but it points to that exact checkout and is not the portable
multi-checkout default.

### Development and testing

The persistent operational tool and the repository's development environment
are separate. Run project commands and tests through the lock-backed environment:

```bash
uv sync --locked --dev
uv run training-sync --help
uv run pytest -q
```

After an intentional dependency change, refresh the lockfile and verify that
the locked environment is reproducible:

```bash
uv lock
uv lock --check
uv sync --locked --dev
```

`uv sync --locked --dev` fails instead of rewriting `uv.lock` when the project
metadata and lockfile disagree. Dependency setup does not read or modify the
local credentials, mappings, IDs, or vault path described below. The separate
`uv tool install` environment is for direct operation and does not replace the
repository lockfile.

### Local configuration

All persistent, machine-specific configuration belongs under:

```text
~/.config/training-sync/
```

The configuration convention is consistent for future settings:

1. A non-empty environment variable is an optional override and has priority.
2. Otherwise, training-sync reads the setting's local file in the directory above.
3. If neither source exists, an optional setting remains unset; a required
   setting fails with an actionable error before provider clients are created.

Keep values out of the repository. Store them by type:

- Credentials and tokens: `garmin-token.json`, `weightxreps-token.json`, and
  provider API-key files when an integration defines one. Treat these files as
  secrets and do not copy them into source control.
- IDs and mappings: `weightxreps-user-id` and
  `weightxreps-exercises.toml`. These are local machine/user configuration.
- Paths: `vault-root`, containing one absolute path to the local Obsidian vault.

Vault-backed commands (`sync` and `weightxreps preview/push`) use
`TRAINING_SYNC_VAULT_ROOT` as the optional override. Without it, save the local
path in `~/.config/training-sync/vault-root`, for example:

```text
~/Documents/obsidian-vault
```

Or override it for one shell/session:

```bash
export TRAINING_SYNC_VAULT_ROOT="$HOME/Documents/obsidian-vault"
```

The environment value wins over the local file, and both forms must resolve to
an absolute path. If neither is configured, training-sync stops before loading
tokens or creating Garmin/Weight x Reps clients. The vault path is local
configuration and is not sent to providers.

When adding a new setting, define its environment variable, local filename,
precedence, validation, and missing-value behavior in `training_sync.config`;
then document the pair here. Do not add personal defaults or hardcoded machine
paths.

## Authentication

The first time you run a Garmin command, it will interactively ask for your Garmin Connect email and password in your terminal.
It will then generate a session token file outside the repo:

```text
~/.config/training-sync/garmin-token.json
```

Future executions reuse this token automatically.

## Usage

### 1. Pushing Strength Workouts to Garmin

Import a strength-training JSON document by providing its file path:

```bash
training-sync garmin import-strength example_workout.json
```

The package uses `src/training_sync/garmin/garmin_exercises.json` to map imported exercise names to Garmin enum IDs. If a mapping is missing or incorrect, update `FITBOD_CUSTOM_MAP` in `src/training_sync/garmin/exercise_mapping.py`.

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
Weight x Reps, the reconciled full day preserves body weight and strength from
both the daily and the remote day, removes previously generated cardio rows,
and creates one new structured row for each supported Garmin cardio activity.
Matching local and remote strength is kept once; missing remote strength is
added to the daily so a fresh-process retry converges. Divergent or remotely
unrepresentable strength stops preflight before either destination is written.

- `type: 1` stores duration-only cardio.
- `type: 2` stores duration plus distance, including the distance value and
  unit. Running maps to `Running`; cycling and virtual rides map to `Cycling`;
  walking, swimming, rowing, and generic cardio map to their corresponding
  existing exercises. Garmin strength activities remain locally rendered and
  use the preserved strength source instead of creating duplicate cardio rows.
  Unsupported or unresolved activity types stop preflight before writes.

After updating the daily, the command saves the complete Weight x Reps day and
verifies body weight, strength weight/reps/set metadata, cardio duration and
distance fields, and submitted comments with a read-back. If the remote save or read-back fails, the updated
daily is intentionally retained so a retry can rebuild the same full-day
payload; the command reports the daily path and the Weight x Reps failure as a
partial sync. Review that error before retrying. The integrated sync does not
create unknown Weight x Reps exercises automatically: unresolved mappings stop
the preflight before either destination is changed.

### 5. Planned Garmin workouts

Chat, a Fitbod screenshot, or a daily note is an input for the assistant, not a
CLI parser contract. The assistant first turns the prescription into versioned
JSON, resolves any genuinely missing choices, and preserves optional provenance
only as local metadata. The JSON is independent of the vault and can be
previewed offline:

```bash
training-sync garmin workout preview examples/planned-strength.json
training-sync garmin workout preview examples/planned-cycling.json
training-sync garmin workout preview examples/planned-running-power.json
```

The preview is the exact flattened sequence submitted to Garmin: warm-up,
work, recovery, cooldown, exercise identity, reps/time/distance/lap
termination, rests, bodyweight, total/per-hand load, and target bounds. An
explicit `garmin_name` is assistant-prepared and user-authorized; it is not
read from the vault or inferred from source prose. Resolution uses existing
mapping/alias precedence before an exact catalog entry, and conflicting or
unknown identities stop the operation.

Create a reusable template, optionally scheduling it on an explicit local
calendar date:

```bash
training-sync garmin workout create examples/planned-strength.json
training-sync garmin workout create examples/planned-strength.json --date 2026-09-13 --yes
```

Without `--yes`, create remains a preview and performs no Garmin mutation. With
`--yes`, the command reads the saved template back before scheduling and reads
the exact calendar occurrence back afterward. The local journal under
`~/.config/training-sync/planned-workouts.json` records account-scoped content
hashes, IDs, and recoverable states; it does not contain source prose,
credentials, or vault paths. A changed plan under the same key is a conflict,
and an uncertain upload is reconciled read-only before any retry.

Template and occurrence management are separate:

```bash
training-sync garmin workout list
training-sync garmin workout show WORKOUT_ID
training-sync garmin workout update WORKOUT_ID examples/planned-strength.json --yes
training-sync garmin workout duplicate WORKOUT_ID --name "Copy" --yes
training-sync garmin workout delete WORKOUT_ID --yes
training-sync garmin calendar list --from 2026-09-13 --to 2026-09-20
training-sync garmin calendar schedule WORKOUT_ID --date 2026-09-13 --yes
training-sync garmin calendar move SCHEDULE_ID --date 2026-09-14 --yes
training-sync garmin calendar remove SCHEDULE_ID --yes
training-sync garmin calendar replace SCHEDULE_ID examples/planned-strength.json --yes
```

These commands manage Garmin Connect templates and calendar occurrences only.
They do not edit completed activities, Obsidian, or Weight x Reps, and this
version has no explicit device-push call. `verified` means Garmin Connect
read-back matched the requested semantics; it does not mean that a watch or
Edge has downloaded or executed the workout. Device compatibility for running
power, indoor context, target display, and the exact rest/side behavior remains
unverified until an explicitly authorized smoke test on a compatible device.

### 6. Weight x Reps

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

### 7. Intervals.icu

Store the personal API key outside the repository, either in the environment
or in a local file (the key is never printed):

```bash
export INTERVALS_API_KEY='redacted-personal-key'
# or: ~/.config/training-sync/intervals-api-key
```

Read-only inventory and exact activity lookup are safe smoke-test commands:

```bash
training-sync intervals list 2026-07-01 2026-07-01
training-sync intervals show ACTIVITY_ID
```

Direct Intervals edits are isolated to that replica. They print a preview until
explicitly authorized:

```bash
training-sync intervals upload ride.fit --external-id GARMIN_ACTIVITY_ID
training-sync intervals update ACTIVITY_ID --name 'Corrected ride' --yes
training-sync intervals delete ACTIVITY_ID
```

Deletion requires an exact remote ID. Deleting a Garmin, Strava, or another
externally sourced Intervals activity can create an Intervals tombstone that
prevents automatic re-import; the preview discloses this and the tool never
removes tombstones automatically. Strava-sourced activities cannot be updated.

For future scoped workflows, name targets repeatedly or select every configured
compatible target explicitly; no empty or implicit mutation scope is accepted:

```bash
training-sync reconcile --target vault --target weightxreps
training-sync reconcile --all
```

## License
MIT License
