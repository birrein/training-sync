# Repository instructions

## Branch naming

Use a branch prefix that reflects the type of work:

- `feature/` for new functionality
- `fix/` for bug fixes
- `hotfix/` for urgent production fixes
- `chore/` for maintenance and tooling
- `refactor/` for code restructuring without behavior changes
- `docs/` for documentation changes
- `test/` for test-only changes

Use the format:

```text
<type>/<scope>-<short-description>
```

Examples:

```text
fix/weightxreps-exercise-resolution
feature/multi-activity-sync
docs/update-readme
```

This convention applies to branch names only; it does not require adopting the full Gitflow workflow.

## Graphify

Graphify is disabled in this workspace. Do not run its CLI, query or update its index. Existing `graphify-out/` files are retained and must not be changed by Graphify.

## Garmin strength workout prescriptions

- Incorporate approach/warm-up sets only when the user explicitly requests them;
  do not add them automatically while planning or publishing a routine. For
  requested exercise-specific approaches, use set `role: "warmup"` so Garmin
  receives native Warm up steps with the exercise, repetitions/termination and
  load. Omitted role or `role: "work"` means working set. Do not infer a set's
  role from a light load or from text, and never group across role boundaries.
- Use normal sequential sets unless the user explicitly requests supersets.
- Group equivalent consecutive sets of the same exercise, repetitions, load,
  load basis and meaningful instructions into Garmin repeat groups. Keep
  warm-up/approach sets distinct from working sets; do not merge different
  prescriptions or manual-lap sets.
- For unilateral work, one series includes both arms/legs: repetitions and load
  are per side, and the prescribed rest follows both sides. Do not double the
  series or repetitions, or supply explicit `sides` to split each series into
  left/right steps, unless the user requests separate-side execution.
- Preserve every prescribed rest exactly. When the rest after an exercise
  differs from its inter-set rest, group the equal sets with
  `skipLastRestStep=true` and add the prescribed transition rest once outside
  the group. With equal rests, use `skipLastRestStep=false` without an extra
  transition. Retain an explicit timed or manual rest after the final workout
  set for watch editing; never invent durations or add both final rests.
- After publishing, read back and verify group counts, repetitions, load,
  combined-side instructions, skip-last-rest flags and the full expanded
  exercise/rest sequence before claiming success.
- Exercise-level RIR supplied after a workout applies only to the last series
  unless the user explicitly provides per-series values. Do not infer effort
  for previous series or count physical left/right records as extra series.
