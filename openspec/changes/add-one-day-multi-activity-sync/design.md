## Context

`training-sync` already has an incomplete `sync DATE` command shape, daily-note helpers, Weight x Reps parsing and JEditor conversion, and remote read-back. The dispatcher does not execute integrated day synchronization, duration/distance Garmin blocks do not fit the strength-only parser, and the legacy design assumes exactly one activity even though a date may contain strength and multiple cardio sessions.

Garmin remains the source of completed activities, an existing Obsidian daily remains the intermediate representation, and Weight x Reps remains a reconciled full-day destination. The implementation must be test-first, must not create missing dailies or exercises silently, and must not report success before structured remote fields are read back.

## Goals / Non-Goals

**Goals:**

- Synchronize every Garmin activity for a date in deterministic order.
- Render one combined `## 🏃 Training` section in the existing daily.
- Preflight all local and remote inputs before any write and use one `--yes` contract for destructive replacements.
- Preserve strength and all cardio when reconstructing the Weight x Reps day.
- Encode duration-only and distance cardio with real structured fields and retain unsupported metrics in `c`.
- Verify exercise, `type`, `t`, `d`, and `dunit` by read-back and expose actionable partial failures.

**Non-Goals:**

- Creating a missing daily note or silently creating unresolved Weight x Reps exercises.
- Adding activity-selection flags or synchronizing only one selected activity.
- Changing unrelated Garmin strength behavior, introducing browser automation, or broadly refactoring the repository.
- Implementing feature code or performing Garmin, vault, or Weight x Reps writes in this planning change.

## Decisions

### D1: Synchronize the complete Garmin day in stable order

Fetch every completed activity for the target date and sort deterministically by its recorded start time, using Garmin activity ID as a tie-breaker. A zero-activity result fails during preflight. This is preferred over the legacy exactly-one rule or selection flags because multiple sessions are normal parts of one training day and the command's unit is the date.

### D2: Produce one combined daily training section

Render all ordered activities into one replacement payload for the existing `## 🏃 Training` section. Require the daily file and heading to exist. Filling an empty section needs no confirmation; replacing non-empty content requires `--yes`. Separate sections per activity were rejected because a single section preserves the current daily contract and gives the downstream parser one deterministic source.

### D3: Complete every preflight before the first write

Before changing the daily, collect and validate Garmin activities, the daily path and current section, credentials, exercise mappings, confirmation requirements, and the complete expected Weight x Reps payload. Unknown or ambiguous exercises fail here. This avoids preventable partial writes and silent exercise creation.

### D4: Use one command-level confirmation contract

`--yes` authorizes replacement of both a non-empty daily training section and an existing remote day. Without it, either destructive condition stops before writes. Independent prompts or separate flags were rejected because one non-interactive contract is easier to reason about and test.

### D5: Reconstruct and preserve the full Weight x Reps day

Build the replacement from preserved strength blocks plus every ordered cardio activity. Do not append only the newest cardio row and do not replace the day with cardio alone. Full reconstruction makes preservation explicit and allows an idempotent retry to converge on one expected state.

### D6: Encode cardio with structured Weight x Reps fields

Cardio with distance maps to set `type: 2` with duration `t` in milliseconds plus the Weight x Reps save payload `d: {val, unit}`. `val` is the distance converted to centimeters and multiplied by 100, while `unit` is the original supported unit string such as `"km"`. Weight x Reps read-back exposes those values as flat `d` and `dunit` fields. Cardio without distance maps to `type: 1` with real duration `t` in milliseconds and without invented distance fields. This replaces the marker-only alternative because Weight x Reps supports the real time/distance representation and those fields can be verified.

### D7: Preserve non-native Garmin metrics in comments

Set comment `c` records the activity name and any Garmin-provided heart rate, elevation, power, calories, and training load that lack dedicated Weight x Reps fields. Missing values are omitted. Dropping the metadata was rejected because it would make the remote record less informative than the daily source.

### D8: Verify structured read-back before success

Read the saved day and compare exercise identity and each expected set's `type`, `t`, `d`, and `dunit`. A mismatch raises an error containing expected and observed details. Mutation acknowledgement alone was rejected because it does not prove the stored representation is correct.

### D9: Keep the daily after a remote failure

After successful preflight, write the daily first and then replace and verify Weight x Reps. If the remote operation fails or verifies incorrectly, retain the updated daily and report partial failure. Rolling the daily back was rejected because a remote timeout can leave the destination outcome uncertain; keeping the local intermediate state supports diagnosis and idempotent retry.

## Risks / Trade-offs

- [Risk] Garmin timestamps or IDs are missing or malformed → Mitigation: reject the activity set during preflight rather than producing unstable ordering.
- [Risk] Full-day replacement could drop remote content not represented in the reconstruction → Mitigation: read and preserve strength and all cardio inputs, require `--yes`, and compare the saved day to the complete expected payload.
- [Risk] Weight x Reps distance-unit encoding differs from assumptions → Mitigation: centralize the encoding and require `d` and `dunit` read-back tests before success.
- [Risk] Daily succeeds while the remote write fails → Mitigation: report partial failure with expected/observed details and make retry deterministic and idempotent.
- [Trade-off] One combined section replaces the whole training section rather than merging individual blocks → Accepted because Garmin is the source of truth for completed activities and replacement is explicit and confirmable.

## Migration Plan

1. Land the CLI and orchestration preflight behind failing focused tests.
2. Add combined daily rendering and confirmation behavior.
3. Add structured cardio models, parser conversion, and full-day preservation.
4. Add remote replacement and structured read-back comparison.
5. Update README usage and run focused tests, the full suite, and a read-only known-day preview.

No data migration is required. If rollout validation fails, revert the feature commits and continue using the existing granular Garmin and Weight x Reps commands; no automatic external writes occur as part of this plan.

## Open Questions

None. The activity scope, confirmation behavior, structured field mapping, verification contract, ordering, and partial-failure policy are approved.
