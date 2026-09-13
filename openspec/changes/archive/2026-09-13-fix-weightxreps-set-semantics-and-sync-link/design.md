## Context

The canonical training model preserves strength sets and exercise-level effort
observations, while the Weight x Reps JEditor format can consolidate repeated
sets through `r` and `s`. That consolidation is only lossless when every set in
the line has the same repetition count and no set-specific effort annotation.
The previous serializer could receive `(12, 13)` in one line or place RPE on a
non-final/consolidated line, which made the remote workout ambiguous.

The synchronization and direct push commands already save the full-day payload
and verify it by reading the remote day back. The authenticated Weight x Reps
username is available through the session GraphQL API, so the CLI can construct
the user's date journal URL after the verified write.

## Goals / Non-Goals

**Goals:**

- Make lossy strength serialization fail before any local or remote write.
- Preserve one row per physical set when repetitions differ.
- Keep exercise-level RIR/RPE on the final physical set only, represented as
  Weight x Reps RPE after the existing RIR-to-RPE projection.
- Include the direct journal URL in successful `sync DATE` and
  `weightxreps push DATE` output.
- Cover each contract with focused regression tests.

**Non-Goals:**

- Change Garmin import semantics, the canonical training model, or the
  Obsidian daily-note format.
- Change Weight x Reps authentication, exercise mapping, or remote mutation
  APIs.
- Reconcile or modify any existing remote workout as part of this artifact.
- Add URL output to preview, failed synchronization, or exercise-resolution
  error responses.

## Decisions

### Validate before serialization

`build_jeditor_rows` validates all strength exercises before constructing any
JEditor rows. `_set_line_to_erow` rejects a line with different repetition
counts and rejects RPE on a consolidated line. This prevents the serializer
from creating an `Unconsolidated reps` comment or silently discarding set
identity.

Alternative considered: preserve the old compact row and add a warning. This
was rejected because a warning would still permit a remote workout that cannot
represent the user's physical sets reliably.

### Require final-set effort annotations

The strength validation requires any RPE/RIR-derived effort annotation to occur
only on the final set line, and that line must contain exactly one physical set.
Earlier sets remain unannotated. This makes the scope explicit and prevents an
exercise-level observation from being copied to every set.

Alternative considered: attach the effort value to the exercise header or
duplicate it across all sets. Neither matches the existing Weight x Reps set
payload or the user's requested logging convention.

### Derive the journal URL from the authenticated session

`WeightxRepsClient.current_username()` reads `getSession.user.uname`, and
`journal_url(date)` builds the URL with URL-escaped username and requested date.
The CLI calls this only after the synchronization use case returns successfully,
which means the existing save and read-back verification have completed. The
URL is included as `weightxreps_url` in the JSON output.

Alternative considered: derive the username from local configuration. This was
rejected because the configured numeric user id is not necessarily the public
journal username and could become stale.

## Risks / Trade-offs

- [Risk] Existing callers may have relied on mixed-repetition rows being
  accepted. → Mitigation: fail explicitly with an actionable message and add
  regression tests for the invalid representation.
- [Risk] A second authenticated GraphQL request is required to obtain the
  username. → Mitigation: perform it only on successful CLI paths and let the
  existing client error handling surface authentication or API failures.
- [Risk] A client double or external integration may not implement
  `journal_url`. → Mitigation: keep the CLI helper optional for test doubles;
  the production Weight x Reps client implements the method.

## Migration Plan

No data migration is required. The change applies to future payloads. Existing
remote days remain untouched until an explicitly confirmed synchronization
replaces them, and the normal read-back verification remains the final gate.

## Open Questions

None for this change. A future change could decide whether to expose the journal
URL in a human-readable non-JSON command, but the current CLI contract is JSON
for the affected synchronization paths.
