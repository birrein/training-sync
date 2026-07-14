# Multi-Activity Day Sync Brainstorm Decision Log

## Background

The active legacy design proposed an integrated `training-sync sync DATE` flow, but its conservative first slice assumed exactly one Garmin activity and represented cycling in Weight x Reps as a marker row. The approved OpenSpec integration discussion revisited those constraints using the current repository, the 2026-07-03 cycling example, and observed Weight x Reps structured cardio fields.

## Decision chain

### Q1: Where should active requirements live?

Options considered were continuing only in `docs/superpowers/`, migrating every historical document, or adopting OpenSpec change-first while migrating only the active design. The approved choice is OpenSpec change-first with only the active design migrated. Historical Superpowers documents remain history; `openspec/changes/add-one-day-multi-activity-sync/` becomes the source of truth for this feature.

### Q2: How many Garmin activities should a day sync?

Options considered were requiring exactly one activity, adding activity-selection flags, or synchronizing every completed activity for the date. The approved choice is every activity for the date. A training day may legitimately contain strength and multiple cardio sessions, so rejecting that day or forcing manual selection would preserve the current gap.

### Q3: What authorizes local replacement?

The daily note must already exist. An empty training section may be filled normally, but replacing a non-empty `## 🏃 Training` section requires `--yes`. This keeps the existing-daily constraint and makes destructive replacement explicit.

### Q4: What authorizes remote replacement?

The same `--yes` flag authorizes replacement when the Weight x Reps day already contains data. One command-level confirmation contract avoids separate prompts and makes non-interactive behavior predictable.

### Q5: What must the Weight x Reps replacement preserve?

The replacement is reconstructed as a complete day. It preserves existing strength activity and includes every cardio activity from Garmin, rather than sending only the newly parsed cycling row or dropping other activity blocks.

### Q6: How should structured cardio sets be encoded?

Cardio with distance uses `type: 2` and carries real duration and distance. Cardio without distance uses `type: 1` and carries real duration. Duration is encoded in milliseconds; distance uses the supported encoded value and unit. This supersedes the legacy marker-only cycling proposal.

### Q7: Where do Garmin metrics without native fields go?

Unsupported Garmin metrics are retained in set comment `c`. When provided, the comment records activity name, heart rate, elevation, power, calories, and training load. Missing metrics are omitted rather than invented.

### Q8: What proves the remote write succeeded?

The command reads the day back and compares exercise identity plus `type`, `t`, `d`, and `dunit`. A mismatch reports expected and observed details and is a failure; accepting a successful mutation response alone is insufficient.

### Q9: What is the write order and partial-failure policy?

All Garmin activities, the existing daily, credentials, exercise mappings, confirmation requirements, and the complete remote payload are preflighted before the first write. The daily is then updated before Weight x Reps because it remains the intermediate representation. If the remote write or verification fails, the updated daily is retained, the command reports partial failure, and a retry must be idempotent.

## Approved design trade-offs

- Prefer a full-day deterministic reconstruction over incremental remote mutation, because preservation and verification are explicit.
- Prefer stable ordering and one combined daily training section over one section per activity, because the daily remains a single parseable source.
- Reject unresolved or ambiguous Weight x Reps exercises before writes; do not silently create exercises.
- Do not implement activity-selection flags, missing-daily creation, broader refactors, feature code, or external writes in this planning change.

All decisions above were approved during the OpenSpec and Superpowers integration design. No further design questions remain for this pilot.
