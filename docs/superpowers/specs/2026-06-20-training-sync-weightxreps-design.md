# Training Sync Weight x Reps Integration Design

## Context

The project is no longer only a Garmin helper. It is becoming a personal training synchronization tool that keeps three systems aligned:

- Garmin Connect as the source of truth for completed activity data.
- The Obsidian vault as the human-readable, auditable training log.
- Weight x Reps as the strength-training journal and analytics destination.

The GitHub repository has already been renamed from `garmin-sync` to `training-sync`. The codebase still has `garmin_sync` package names and a `garmin-sync` CLI; this design covers how to evolve the project without breaking the current working commands.

## Goals

- Rename the project identity to `training-sync`.
- Add a real Weight x Reps integration using official OAuth with PKCE.
- Support a one-day sync flow that keeps Garmin, the vault, and Weight x Reps aligned.
- Support the existing Fitbod screenshot workflow by importing the extracted workout into Garmin first, then syncing the verified result onward.
- Keep the architecture modular and testable without adopting full Clean Architecture ceremony.
- Preserve temporary compatibility for current `garmin-sync --fetch` and `garmin-sync --weight` commands while the new CLI settles.

## Non-Goals

- Do not build an MCP server in the first implementation.
- Do not support weekly or date-range writes in the first implementation.
- Do not create missing daily notes automatically.
- Do not bypass Weight x Reps OAuth by using browser cookies or scraped sessions.
- Do not write directly from Fitbod screenshots to Weight x Reps.

## CLI Shape

The new CLI entrypoint is `training-sync`.

Primary command:

```bash
training-sync sync 2026-06-19
```

This synchronizes one date end to end:

```text
Garmin activity for date
-> ensure/update vault daily Training block
-> parse/render Weight x Reps-compatible log
-> write the full day to Weight x Reps
-> verify saved Weight x Reps day
```

Support commands:

```bash
training-sync garmin fetch 2026-06-19
training-sync garmin import-strength fitbod-payload.json
training-sync vault sync 2026-06-19
training-sync weightxreps auth
training-sync weightxreps preview 2026-06-19
training-sync weightxreps push 2026-06-19
```

Temporary compatibility:

```bash
garmin-sync --fetch 2026-06-19
garmin-sync --weight 2026-06-19
```

These aliases should continue to work during the migration, but new documentation should point to `training-sync`.

## Main Flows

### Flow A: Garmin Activity Already Correct

Use this when Garmin already has the completed activity and any strength sets are already correct.

```bash
training-sync sync 2026-06-19
```

Steps:

1. Read Garmin activities for the date.
2. Resolve the target activity or activities for the daily log.
3. Normalize Garmin data into domain objects.
4. Ensure the vault daily `## 🏃 Training` block is present and current.
5. Parse or render the final Weight x Reps-compatible block from the vault state.
6. Convert the day to Weight x Reps `JEditorSaveRow` rows.
7. Write the full date to Weight x Reps.
8. Read the Weight x Reps day back and verify core fields.

### Flow B: Strength Workout Comes From Fitbod Screenshots

The user provides screenshots in chat. The agent extracts a Fitbod-like JSON payload from the images.

```bash
training-sync garmin import-strength fitbod-payload.json
training-sync sync 2026-06-19
```

Steps:

1. Extract date, title, exercises, sets, reps, weights, and bodyweight markers from the screenshots.
2. Build a local JSON payload.
3. Import the payload into the Garmin strength activity for that date.
4. Read Garmin back and verify title, active set count, exercise names, reps, and weights.
5. Run the normal `sync DATE` flow.

Weight x Reps never receives data directly from screenshots. The data first goes through Garmin and the vault so all three systems stay aligned.

## Architecture

Use a modular use-case plus adapter architecture. This is inspired by Clean Architecture, but intentionally avoids heavy ceremony.

```text
src/training_sync/
  cli.py

  use_cases/
    sync_day.py
    import_fitbod_strength.py

  domain/
    training_entry.py
    strength_workout.py
    body_weight.py

  garmin/
    auth.py
    client.py
    payloads.py
    exercise_mapping.py

  vault/
    daily.py
    training_block.py

  weightxreps/
    auth.py
    client.py
    jeditor.py

  renderers/
    obsidian_markdown.py
    weightxreps_text.py
```

Responsibilities:

- `domain/`: pure data objects and rules. No API calls, filesystem calls, or CLI output.
- `use_cases/`: orchestrates flows such as `sync_day` and `import_fitbod_strength`.
- `garmin/`: concrete Garmin Connect adapter, auth, activity lookup, exercise set payloads, body-weight reads.
- `vault/`: concrete Obsidian vault adapter for locating and updating daily notes.
- `weightxreps/`: OAuth, GraphQL client, and `JEditorSaveRow` conversion.
- `renderers/`: converts domain entries into Markdown or Weight x Reps text.
- `cli.py`: parses args, calls use cases, and prints user-facing output.

Do not create abstract interfaces for every adapter up front. Use simple fakes in tests and introduce protocols/interfaces only when they remove real complexity.

## Weight x Reps OAuth

Use the official Weight x Reps OAuth2 endpoint with PKCE.

Auth command:

```bash
training-sync weightxreps auth
```

Configuration:

```text
~/.config/training-sync/config.toml
~/.config/training-sync/weightxreps-token.json
```

Example config:

```toml
[weightxreps]
client_id = "..."
redirect_uri = "http://127.0.0.1:8765/callback"
scopes = "jread,jwrite"
```

The auth command opens the browser, handles the callback locally, exchanges the authorization code for tokens, and stores tokens outside the repo.

Token rules:

- Never commit tokens.
- Never print access tokens or refresh tokens.
- Refresh tokens automatically when possible.
- If refresh fails, ask the user to run `training-sync weightxreps auth`.

## Weight x Reps Write Semantics

Write command:

```bash
training-sync weightxreps push 2026-06-19
```

Preview command:

```bash
training-sync weightxreps preview 2026-06-19
```

The push command reads the vault daily block for that date, converts it to Weight x Reps `JEditorSaveRow` rows, and calls the GraphQL mutation that saves editor rows.

Replacement rule:

- The first version syncs by date and replaces the full Weight x Reps day.
- `weightxreps push DATE` should require confirmation or `--yes` if the remote day already has content.
- `sync DATE` may replace the day because reconciliation is its contract, but it must report that it replaced existing content.

Verification:

After writing, read the day back with `jread` and confirm:

- the date exists,
- bodyweight is present when expected,
- exercise names or IDs match the intended day,
- representative set counts and reps match.

Only report success after this read-back verification passes.

## JEditor Mapping

Weight x Reps documents `JEditorSaveRow` with these relevant shapes:

- Bodyweight: `{ bw: 76, lb: 0 }`
- Day log: `{ on: "YYYY-MM-DD", did: [...] }`
- Exercise block: `{ eid: number, erows: [...] }`
- Set row: weight/reps/sets fields including `v`, `r`, `s`, optional `lb`, and optional `usebw`.

Implementation should start with the subset needed by current logs:

- bodyweight in kg,
- exercise blocks,
- simple weight x reps sets,
- bodyweight sets,
- one date at a time.

Technical debt:

- Current set rows are written as Weight x Reps `WEIGHT_X_REPS` sets with `type: 0`.
- Before supporting time-based or distance-based exercises, promote the set type into the parsed/domain model instead of hard-coding it in the JEditor builder.
- Future mapping should cover Weight x Reps set types explicitly, at least `WEIGHT_X_REPS = 0`, `WEIGHT_X_TIME = 1`, and `WEIGHT_X_DISTANCE = 2`, and verification should compare the expected type per set instead of assuming every saved set is `0`.

Exercise ID handling:

- Prefer lookup by existing Weight x Reps exercise name.
- If a matching exercise does not exist and the API supports `{ newExercise: "..." }`, use that as the creation path.
- If creation or lookup is ambiguous, stop with an actionable error rather than guessing.
- For the detailed exercise-alias and confirmation design, see `docs/superpowers/specs/2026-06-22-weightxreps-exercise-resolution-design.md`.

## Error Handling

- Garmin has no clear activity for date: stop and ask for clarification.
- Vault daily does not exist: stop; do not create automatically in this first version.
- Vault Training block is missing or malformed: report the issue and avoid writing Weight x Reps.
- Weight x Reps OAuth is missing or expired: refresh, then ask for `weightxreps auth` if refresh fails.
- Weight x Reps day has existing content: replace only according to the command contract and confirmation rules.
- Exercise mapping is uncertain: stop before writing.
- Post-write verification fails: report partial write risk and show the expected versus observed summary.

## Testing Strategy

Unit tests:

- Fitbod-like JSON to `StrengthWorkout`.
- Garmin strength payload construction.
- Garmin activity to domain `TrainingEntry`.
- Vault training block parser and updater.
- Weight x Reps text/block to domain.
- Domain to `JEditorSaveRow`.
- OAuth PKCE helper behavior.

Use-case tests with fakes:

- `sync_day` with fake Garmin, fake vault, fake Weight x Reps.
- `import_fitbod_strength` with fake Garmin verifying set updates.
- Existing Weight x Reps day requires confirmation in `push`, but `sync` replaces by contract.

Manual verification:

- OAuth login against the real Weight x Reps account.
- Preview for a known date.
- Real write for one known training day.
- Read-back verification confirms the saved day.

## Migration Plan

1. Add `training-sync` console script while keeping `garmin-sync`.
2. Move code from `garmin_sync` toward `training_sync` in small commits.
3. Add subcommands without removing current flags.
4. Implement Weight x Reps auth and preview before write.
5. Implement Weight x Reps real write with read-back verification.
6. Update README, skill instructions, and any local paths from `garmin-sync` to `training-sync`.
7. Consider renaming the local folder from `/Volumes/ssd1/dev/garmin-sync` to `/Volumes/ssd1/dev/training-sync` after code and docs are updated.

## Open Risks

- The exact Weight x Reps GraphQL schema and mutation shape must be confirmed against the live schema or source before implementation.
- Exercise lookup and creation may require more GraphQL work than the minimal `JEditorSaveRow` docs show.
- Replacing a full Weight x Reps day is convenient but potentially destructive; confirmation and verification must be solid.
- Renaming the Python package can be noisy; compatibility aliases should keep daily use working during migration.
