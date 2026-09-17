## ADDED Requirements

### Requirement: Publish provider-compatible workout fields
The system SHALL serialize planned workout writes using Garmin-compatible field types and units while preserving the validated prescription. Internal exercise labels, load basis and provenance MUST NOT become unsupported provider fields. Original exercise names and necessary load/side instructions SHALL remain in published descriptions. These guarantees SHALL apply to supported flat steps and repeat-group children across creation, update, duplication and date-specific variants.

#### Scenario: Mass and repetition prescription
- **WHEN** a strength step prescribes 50 kg total for eight repetitions
- **THEN** the provider request represents 50 kilograms using a structured kilogram unit, keeps eight as repetition termination, and does not send text-only preferred termination units

#### Scenario: Substitute and bodyweight
- **WHEN** Dragon Flag at bodyweight explicitly selects Reverse Crunch on a Bench
- **THEN** Garmin receives the catalog identity and an explicit Dragon Flag comment, without inventing an external weight or sending unsupported internal metadata

#### Scenario: Nested supported steps
- **WHEN** supported strength repeat groups contain weighted steps and timed or manual rests
- **THEN** every child uses compatible field representations and preserves iteration count, order and final-rest behavior

#### Scenario: Endurance regression protection
- **WHEN** a supported cycling or running workout uses time, distance or manual termination and an intensity target
- **THEN** serialization preserves termination and target independently without strength-specific unit conversions corrupting either

### Requirement: Normalize provider units for semantic verification
The system SHALL compare weights using explicitly supported provider unit representations, including structured kilogram units and legacy gram representations. Unknown or contradictory units MUST fail verification rather than default to grams. Equivalent wire encodings MUST NOT change canonical plan identity or permit missing instructions, wrong loads, changed rests or altered groups to pass verification.

#### Scenario: Equivalent mass encoding
- **WHEN** 50 kg in the plan reads back as 50 with a structured kilogram unit
- **THEN** verification accepts the same mass and retains total/per-hand meaning from preserved instructions

#### Scenario: Real mismatch
- **WHEN** the saved load differs, units are unknown, or a required Dragon Flag or per-hand instruction is absent
- **THEN** verification fails and scheduling is not attempted

#### Scenario: Recovery after corrected transport
- **WHEN** an uncertain journal entry has exactly one remote marker match with verified equivalent semantics using the corrected unit encoding
- **THEN** retry adopts that template and reuses its matching calendar occurrence instead of uploading another template

### Requirement: Preserve bounded provider failure diagnostics
Failed workout writes SHALL expose the operation stage, available HTTP status, provider error type and reference ID through bounded redacted diagnostics. Diagnostic detail MUST remain distinct from outcome certainty: an HTTP 500 MUST NOT prove the write was absent. Reconciliation SHALL retain the original diagnostic when no match is found or inventory is incomplete, and MUST NOT trigger a blind upload retry. Credentials, tokens, headers, personal data and complete request/response bodies MUST NOT be exposed or persisted as diagnostics.

#### Scenario: Provider parsing error
- **WHEN** upload raises HTTP 500 with MismatchedInputException and a provider reference ID
- **THEN** the failure reports those safe details together with template/calendar state and reconciliation result

#### Scenario: Uncertain inventory
- **WHEN** read-only reconciliation finds no exact semantic match within an incomplete inventory
- **THEN** the result remains unresolved, keeps the original upload diagnostic, and makes no additional upload

#### Scenario: Sensitive exception text
- **WHEN** an exception includes authorization headers, tokens or a request body alongside a provider error
- **THEN** output and journal retain only allowlisted diagnostic fields and bounded safe explanatory text
