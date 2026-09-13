## Why

Weight x Reps can lose the physical-set meaning of a strength workout when
different repetition counts are consolidated into one row, producing
"Unconsolidated reps" and obscuring which set received the user's RIR/RPE.
The synchronization result also needs to expose the exact Weight x Reps journal
entry so the user can open and verify the saved workout directly.

## What Changes

- Preserve one Weight x Reps row per physical set whenever repetitions differ
  or a set-level RIR/RPE value must be represented.
- Reject ambiguous strength serialization before a remote write instead of
  emitting a row with mixed repetition counts.
- Associate RIR/RPE only with the final physical set of an exercise, matching
  the training-log contract.
- Return the direct Weight x Reps journal URL after successful, read-back-
  verified synchronization from both the day sync and direct push CLI paths.
- Add regression coverage for serialization validation, final-set RPE/RIR
  placement, journal URL construction, and CLI output.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `weightxreps-cardio-sync`: preserve exact strength-set semantics, constrain
  RIR/RPE to the final physical set, and expose the verified journal URL.

## Impact

- `src/training_sync/weightxreps/jeditor.py`: validate strength rows before
  serialization and prevent ambiguous mixed-repetition rows.
- `src/training_sync/weightxreps/client.py`: construct the authenticated
  user's journal URL.
- `src/training_sync/cli.py`: include the direct journal URL in successful
  synchronization output.
- `tests/test_weightxreps_jeditor.py`,
  `tests/test_weightxreps_client.py`, and
  `tests/test_training_sync_cli.py`: regression coverage for the new
  contracts.
- No changes to Garmin activity data, Obsidian daily notes, credentials, or
  Weight x Reps remote records are required by the OpenSpec artifact itself.
