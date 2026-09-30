## Purpose

Let users explicitly record selected foods in Garmin Connect using their existing Training Sync session, while protecting prior entries and reporting success only after Garmin confirms the saved foods.

## ADDED Requirements

### Requirement: Resolve foods and servings before logging
The system SHALL prefer an exact food and compatible serving already present in the account's Garmin daily serving list, then search Garmin's catalog when no exact saved food is available. It MUST reject missing, ambiguous, invalid, or non-positive quantities without mutating Garmin.

#### Scenario: Exact food and serving match
- **WHEN** a requested food and quantity match one catalog food and serving
- **THEN** the system resolves that food and a quantity in the serving's units for logging

#### Scenario: Prefer existing account food
- **WHEN** the daily serving list contains one exact food with a compatible serving while catalog search contains multiple same-name foods
- **THEN** the system uses the existing account food and serving

#### Scenario: Ambiguous or missing match
- **WHEN** a requested food has no compatible match or more than one equally exact match
- **THEN** the system reports the candidates or missing match and sends no write

### Requirement: Log at an explicit local date and time
The system SHALL accept an explicit local date and time, select the enabled Garmin meal whose configured window contains that time, and use the account's food metadata for the selected catalog entries. If no window matches, it SHALL select the unique enabled meal named `SNACKS` only when that meal has no configured time window. It MUST reject ambiguous meal windows or a time with no unambiguous meal assignment.

#### Scenario: Time falls in a meal window
- **WHEN** the requested local time falls inside one enabled meal window
- **THEN** each food is assigned to that meal with the requested date and time

#### Scenario: Unconfigured snacks window
- **WHEN** no meal window matches and exactly one enabled `SNACKS` meal has no configured window
- **THEN** the system assigns the entries to `SNACKS`

#### Scenario: Ambiguous meal assignment
- **WHEN** windows overlap, or there is no matching window and no unique unconfigured `SNACKS` meal
- **THEN** the system explains the conflict and sends no write

### Requirement: Prevent duplicate and preserve existing food entries
The system MUST inspect the current daily log before writing, preserve all prior entries, and refuse to add an item already present with the same food, serving, quantity, meal, and time. The system SHALL submit all requested additions together as one operation.

#### Scenario: Existing matching item
- **WHEN** a requested item already appears in the log at the requested meal and time
- **THEN** the system reports the duplicate and performs no write

#### Scenario: New items preserve prior log
- **WHEN** all requested items are absent
- **THEN** the system submits the requested additions without replacing existing entries

#### Scenario: Duplicate request item
- **WHEN** the request repeats the same food, serving, and quantity at the same meal time
- **THEN** the system asks the user to combine the amounts and sends no write

### Requirement: Preview before authorized write
The food-log command MUST preview resolved foods and meal assignment by default and SHALL write only when the user explicitly passes `--yes`.

#### Scenario: Preview by default
- **WHEN** the food-log command runs without `--yes`
- **THEN** it shows the resolved entries and performs no write

#### Scenario: Explicitly authorized logging
- **WHEN** the user supplies `--yes` after reviewing the proposed entries
- **THEN** the command performs the single verified log operation

### Requirement: Reconcile uncertain writes and verify saved entries
The system MUST read the daily log after a write and report success only when every requested item appears with the expected food, serving, quantity, meal, date, and time. If the write response is uncertain, it MUST reconcile using GET before considering any further write and MUST NOT blindly retry.

#### Scenario: Successful write verification
- **WHEN** the write succeeds and read-back contains every requested item with expected fields
- **THEN** the result reports verified entries and Garmin-reported nutrition totals

#### Scenario: Uncertain or partial write
- **WHEN** the write response is lost, rejected, or read-back is incomplete
- **THEN** the system reports the verified, missing, or uncertain items and does not repeat the write

### Requirement: Isolate Garmin Nutrition transport
The system SHALL isolate Garmin Nutrition endpoint paths and payload serialization behind the Garmin nutrition adapter and SHALL reuse existing Garmin authentication without exposing or persisting credentials through the food command.

#### Scenario: Nutrition adapter operation
- **WHEN** a food search, log, or verification is performed
- **THEN** its Nutrition API request is issued by the adapter using the existing authenticated Garmin client
