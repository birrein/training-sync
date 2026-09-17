# Evidence notes

- The accepted, rejected and read-back fixtures are sanitized contract evidence; they contain no account identifiers, tokens, headers or private source prose.
- The successful Garmin correction on 2026-09-16 changed several wire fields together: kilogram value/unit, null preferred termination unit, removal of adapter-only fields and strength `displayOrder`. It validates the combined representation only; these fixtures do not claim isolated causal proof for any single field.
- The Dragon Flag fixture records the already-approved catalog identity `CRUNCH / REVERSE_CRUNCH_ON_A_BENCH` and keeps the original exercise plus substitute visible in the description.
- No additional live workout was uploaded while applying this change. Any live validation remains read-only and does not establish device behavior for fields not covered by the accepted shape.
- Read-only live verification on 2026-09-16 read template `1700608747` and calendar occurrence `1780026765`: 27 remote steps matched the corrected projection, and the occurrence resolved to `2026-09-16` with workout `1700608747`. No create, update, delete or schedule endpoint was called.
- Final validation evidence: `uv run python -m pytest -q` passed with 375 tests; `openspec validate fix-garmin-workout-payload --strict` passed; `git diff --check` reported no whitespace errors. Flat strength, cycling and running paths are covered by focused tests, while recursive provider-field sanitization is present for supported nested children. The separate grouping implementation remains outside this change and its dirty planning artifacts were preserved; no new grouping shape or rest policy was introduced here.

## Integration and archive validation — 2026-09-16

- Integrated `feature/garmin-strength-set-grouping` into `main`, retaining its existing archive and explicit timed/manual final-rest policy. The earlier 375-test result above describes the pre-integration baseline.
- Reproduced and corrected two integration regressions with tests first: grouped per-hand children leaking the internal `side` field, and grouped duplication rejecting equivalent kilogram/gram read-back units. Both now pass without weakening description or repeat-layout verification.
- Provider-boundary fakes now inspect expanded grouped children during creation, update, duplication and date-specific replacement. Tests retain group counts, final rests, per-hand instructions and unrelated metadata.
- The integrated suite passes with 430 tests (`uv run python -m pytest -q`). Strict main-spec validation passes for all 11 capabilities; whitespace checks pass. These remain offline/fake-client checks, not proof of grouped device behavior. No live Garmin writes were performed during integration or archiving.
