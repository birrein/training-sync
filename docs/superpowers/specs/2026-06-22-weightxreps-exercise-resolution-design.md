# Weight x Reps Exercise Resolution Design

## Context

Training Sync can now push a vault training day to Weight x Reps. The current implementation resolves exercises by exact name when Weight x Reps already returns an exercise ID for that date, and otherwise emits `newExercise`.

That is risky. Weight x Reps creates a new exercise when `newExercise` is saved, so small name differences can create duplicate exercises such as `Hip Thrust`, `Barbell Hip Thrust`, and `Barbell Hip Thrust with Bench`.

The desired behavior is:

- known exercise aliases sync automatically,
- unknown or ambiguous exercises stop before writing,
- the CLI emits enough structured information for an AI agent to ask the user a clear follow-up,
- once the user chooses, the mapping is saved so the same question is not asked again.

## Goals

- Add a durable local Weight x Reps exercise mapping.
- Resolve incoming exercise names to existing Weight x Reps exercise IDs before building `JEditorSaveRow` payloads.
- Avoid creating new Weight x Reps exercises without explicit confirmation.
- Make unresolved exercise output machine-readable and easy for an AI agent to continue from.
- Keep the normal `weightxreps push DATE --yes` path automatic when all exercises are mapped.

## Non-Goals

- Do not merge or rename existing Weight x Reps exercises in the first version.
- Do not infer mappings from Garmin exercise enums alone.
- Do not create a global/public exercise taxonomy.
- Do not require an interactive terminal prompt for normal agent-driven use.
- Do not write mappings into the repository by default.

## Mapping File

Store the user-specific mapping outside the repo:

```text
~/.config/training-sync/weightxreps-exercises.toml
```

Use one table per canonical Weight x Reps exercise:

```toml
[[exercises]]
weightxreps_name = "Barbell Hip Thrust"
weightxreps_id = 157721
aliases = [
  "Barbell Hip Thrust with Bench",
  "Hip Thrust",
  "BB Hip Thrust"
]
notes = "Preferred canonical lower-body hip thrust entry."

[[exercises]]
weightxreps_name = "Hanging Knee Raise"
weightxreps_id = 158078
aliases = [
  "Hanging Knee Raise",
  "Hanging Leg Raise"
]
```

Rules:

- `weightxreps_name` is required.
- `weightxreps_id` is optional but preferred once known.
- `aliases` should include source names from Fitbod, Garmin, vault text, and any common manual variants.
- Aliases are matched case-insensitively after normalization.
- If `weightxreps_id` exists but Weight x Reps no longer returns that exercise, stop and ask for a mapping refresh instead of guessing.

## Resolution Flow

Before `build_jeditor_rows`, run an exercise resolver with:

- parsed exercises from the vault day,
- the local mapping file,
- the remote Weight x Reps exercise catalog available to the authenticated user.

Resolution order:

1. Normalize the incoming exercise name.
2. Match against local aliases and canonical `weightxreps_name`.
3. If the local mapping has a valid `weightxreps_id`, use it.
4. If the local mapping has only a `weightxreps_name`, resolve that name against the remote catalog and return a suggested mapping update with the discovered ID.
5. If no local mapping exists, try exact normalized remote-name match.
6. If exact remote match exists, use it and optionally suggest persisting an alias.
7. If no exact match exists, find similar remote candidates.
8. If candidates are ambiguous or absent, stop before writing and emit structured resolution output.

The resolver returns either:

- a complete `{ incoming_name: weightxreps_id }` map, or
- a resolution-required result with one or more unresolved exercises.

## Candidate Matching

Candidate search should be conservative. It should help the user decide, not silently decide.

Normalization:

- trim whitespace,
- remove a leading `#`,
- lowercase,
- collapse repeated whitespace,
- ignore punctuation differences,
- do not normalize abbreviations unless they are present as explicit aliases in the mapping file.

Similarity candidates:

- include exact normalized token matches,
- include high string-similarity matches,
- prefer candidates sharing important tokens such as `squat`, `row`, `press`, `curl`, `raise`, `thrust`, `deadlift`,
- cap results to the best 5 candidates.

Do not auto-map fuzzy matches in the first version. Fuzzy matches are only presented as candidates.

## Agent-Oriented Output

When resolution is required, the CLI should not print an unstructured prose-only error. It should print JSON to stdout or stderr and exit with a distinct non-zero code.

Example:

```json
{
  "status": "exercise_resolution_required",
  "date": "2026-06-20",
  "unresolved": [
    {
      "incoming_exercise": "Barbell Hip Thrust with Bench",
      "normalized_name": "barbell hip thrust with bench",
      "reason": "no_local_mapping",
      "candidates": [
        {
          "weightxreps_id": 157721,
          "weightxreps_name": "Barbell Hip Thrust",
          "match_reason": "similar_name"
        },
        {
          "weightxreps_id": 157700,
          "weightxreps_name": "Hip Thrust",
          "match_reason": "shared_tokens"
        }
      ],
      "allowed_actions": [
        "map_to_existing",
        "create_new",
        "skip_workout"
      ]
    }
  ],
  "suggested_agent_question": "How should I resolve 'Barbell Hip Thrust with Bench': map it to an existing candidate, create it as a new Weight x Reps exercise, or skip this sync?"
}
```

This gives an AI agent enough context to ask the user one clear follow-up. It also makes the next action explicit.

## User Decisions

Supported decisions:

- `map_to_existing`: add the incoming name as an alias of an existing Weight x Reps exercise.
- `create_new`: mark the incoming name as allowed to create a new Weight x Reps exercise.
- `skip_workout`: abort the current push without writing anything.

The preferred agent flow is:

1. Run the push or a dedicated resolution command.
2. If JSON says `exercise_resolution_required`, ask the user which allowed action to take.
3. Update the local mapping file based on the answer.
4. Re-run the push.

The first implementation can work with agent-edited TOML, but the intended CLI helpers are:

```bash
training-sync weightxreps exercises resolve 2026-06-20
training-sync weightxreps exercises map \
  --incoming "Barbell Hip Thrust with Bench" \
  --existing-id 157721
training-sync weightxreps exercises create \
  --incoming "New Exercise Name"
```

These commands should write deterministic TOML changes and are the preferred path once the resolver behavior is covered by tests. Until they exist, an AI agent can apply the same mapping update by editing the TOML file.

## Creating New Exercises

Creating new exercises should be opt-in.

Rules:

- `weightxreps push DATE --yes` does not imply permission to create unmapped exercises.
- A new exercise can be created only when the local mapping explicitly marks it as new or when a command receives an explicit create flag.
- The first implementation should prefer a mapping entry over a broad `--create-new-exercises` flag.

Suggested TOML shape:

```toml
[[exercises]]
weightxreps_name = "New Exercise Name"
create_if_missing = true
aliases = [
  "New Exercise Name"
]
```

When the push succeeds and Weight x Reps returns or exposes the new ID through the remote catalog, the mapping should be updated with `weightxreps_id`.

## Architecture

Add a small resolver layer inside `training_sync.weightxreps`:

```text
src/training_sync/weightxreps/
  exercise_mapping.py
  exercise_resolution.py
```

Responsibilities:

- `exercise_mapping.py`: read/write the TOML file, normalize aliases, validate duplicates.
- `exercise_resolution.py`: combine parsed exercise names, local mappings, remote exercise catalog, and candidate scoring into a resolved map or resolution-required result.
- `weightxreps_push.py`: call the resolver before preview/build rows.
- `jeditor.py`: continue receiving resolved `{ exercise_name: eid }` and avoid making resolution decisions.
- `client.py`: expose the remote exercise catalog needed by the resolver.

Keep mapping resolution separate from `build_jeditor_rows`; the builder should stay a dumb converter from parsed day plus resolved IDs to `JEditorSaveRow`.

Remote catalog source:

- Prefer the Weight x Reps `getExercises(uid)` GraphQL query when the authenticated user ID is available from config or account discovery.
- If the full user ID path is not implemented yet, use the existing `jeditor` query with a wide date range as a fallback catalog of recently used exercises.
- The resolver must mark the catalog source in debug output so agents know whether candidate search was full or partial.
- A partial catalog is allowed for alias resolution, but should be called out when asking the user to create a brand-new exercise.

## CLI Behavior

Default `push` behavior:

```bash
training-sync weightxreps push 2026-06-20 --yes
```

- if all exercises resolve, write normally,
- if any exercise is unresolved, write nothing and emit structured JSON,
- if an exercise is explicitly marked `create_if_missing = true`, allow `newExercise` for that exercise only.

Preview behavior:

```bash
training-sync weightxreps preview 2026-06-20
```

- should run the same resolver,
- should show unresolved exercises before showing final rows,
- should not create anything.

Agent-facing behavior:

- Prefer JSON output when resolution fails.
- Keep the message deterministic, with stable fields and allowed actions.
- Avoid terminal-only prompts as the primary path.

## Error Handling

- Mapping file missing: treat as empty mapping.
- Mapping file invalid TOML: stop with a clear file path and parse error.
- Duplicate alias in mapping file: stop and show both canonical targets.
- Mapped ID not present in remote catalog: stop and ask to refresh or remap.
- Mapped name conflicts with a different remote ID: stop and ask for confirmation.
- Multiple incoming exercises map to the same Weight x Reps exercise: allow it only if they are aliases in the same workout and warn in preview.
- User chooses `create_new` while similar candidates exist: require explicit mapping entry or command, not accidental confirmation through `--yes`.

## Testing Strategy

Unit tests:

- mapping file load with aliases and IDs,
- missing mapping file behaves as empty,
- duplicate alias validation fails,
- exact alias resolves to ID,
- mapped name resolves to remote ID when ID is omitted,
- unknown exercise returns structured `exercise_resolution_required`,
- fuzzy candidates are returned but not auto-selected,
- `create_if_missing = true` allows a controlled `newExercise`.

Use-case tests:

- `weightxreps push` writes when all exercises resolve,
- `weightxreps push` writes nothing when one exercise is unresolved,
- `preview` reports unresolved exercises without saving,
- agent JSON output contains `status`, `date`, `unresolved`, `candidates`, `allowed_actions`, and `suggested_agent_question`.

Manual verification:

- run against a day where all exercises are mapped,
- run against a day with one intentionally unmapped exercise and confirm no Weight x Reps write happens,
- add an alias mapping, re-run, and confirm the existing Weight x Reps exercise receives the sets,
- explicitly create one new exercise only after confirming it is not a duplicate.

## Implementation Decisions

- Exact remote-name matches may be used for the current push without confirmation.
- Persisting a new alias to TOML should happen only after a user/agent decision, except when a helper command is explicitly invoked.
- Before the CLI writes the TOML file, it should create a timestamped `.bak` copy next to it.
- The first complete implementation should support the resolver, structured failure output, and safe mapping writes; automatic merge/rename of existing Weight x Reps exercises remains out of scope.
