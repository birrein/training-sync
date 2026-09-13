# weightxreps-cardio-sync Delta Specification

## ADDED Requirements

### Requirement: Preserve physical strength set boundaries

The system MUST preserve the physical set boundaries of strength exercises in
Weight x Reps serialization. Each strength JEditor line MUST contain one
repetition count. When physical sets have different repetition counts, the
projection MUST provide one line per physical set, and the serializer MUST
reject input that combines those counts into one line before any destination
write.

#### Scenario: Different repetitions remain separate physical rows

- **WHEN** an exercise has physical sets of 12 and 13 repetitions at the same
  weight and the projection provides them as two set lines
- **THEN** the Weight x Reps payload contains two strength rows with `r: 12,
  s: 1` and `r: 13, s: 1`

#### Scenario: Mixed repetitions are rejected before writing

- **WHEN** a strength line contains repetitions `(12, 13)`
- **THEN** serialization fails with an explicit different-repetition error
- **AND** it does not generate an `Unconsolidated reps` row

### Requirement: Associate effort with the final physical set

The system MUST attach an exercise's RIR/RPE-derived effort value only to the
final physical set. The final set line MUST represent exactly one physical set,
and the system MUST reject effort annotations placed on an earlier or
consolidated line.

#### Scenario: Final single set receives RPE

- **WHEN** an exercise has several physical sets and its RIR/RPE observation is
  represented on the final one-repetition set line
- **THEN** the generated Weight x Reps payload contains `rpe` only on that
  final row
- **AND** earlier rows do not contain `rpe`

#### Scenario: Non-final effort annotation is rejected

- **WHEN** an exercise has RPE/RIR-derived effort on a set line before its
  final physical set
- **THEN** serialization fails with an error requiring the final set

#### Scenario: Consolidated effort annotation is rejected

- **WHEN** an exercise has RPE/RIR-derived effort on a line representing more
  than one physical set
- **THEN** serialization fails with an error requiring a single final set

### Requirement: Report the verified Weight x Reps journal URL

The affected CLI commands MUST include `weightxreps_url` with the direct URL
`https://weightxreps.net/journal/<username>/<YYYY-MM-DD>` for the authenticated
Weight x Reps user and requested date after a Weight x Reps save and read-back
verification complete successfully.

#### Scenario: Full-day sync reports its direct journal entry

- **WHEN** `training-sync sync DATE` completes the existing save and read-back
  verification successfully
- **THEN** its JSON output contains the direct `weightxreps_url` for the
  authenticated user and `DATE`

#### Scenario: Direct Weight x Reps push reports its journal entry

- **WHEN** `training-sync weightxreps push DATE --yes` completes successfully
- **THEN** its JSON output contains the direct `weightxreps_url` for the
  authenticated user and `DATE`
