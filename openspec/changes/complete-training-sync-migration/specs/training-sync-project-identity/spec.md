## ADDED Requirements

### Requirement: Canonical Python project identity
The project SHALL be distributed as `training-sync`, SHALL expose production Python code only under the `training_sync` namespace, and SHALL contain no runtime dependency on a `garmin_sync` package.

#### Scenario: Installed distribution metadata
- **WHEN** the project is installed into a clean Python environment
- **THEN** its installed distribution name is `training-sync`
- **AND** `training_sync` imports successfully
- **AND** `garmin_sync` is not provided by the project

#### Scenario: Garmin adapter imports
- **WHEN** the Training Sync CLI or use cases load Garmin authentication, fetching, weight, or strength-import behavior
- **THEN** those components are imported from `training_sync.garmin`
- **AND** existing Garmin behavior remains covered by the migrated tests

### Requirement: Canonical command-line interface
The installed project SHALL expose `training-sync` as its only project console command and SHALL accept only the documented modern command groups.

#### Scenario: Modern command surface
- **WHEN** the user runs `training-sync --help`
- **THEN** the CLI lists the `sync`, `garmin`, and `weightxreps` command groups
- **AND** their documented subcommands remain available

#### Scenario: Legacy executable is absent
- **WHEN** the project is installed into a clean environment
- **THEN** the installation does not create a `garmin-sync` console script

#### Scenario: Legacy argument forms are rejected
- **WHEN** the user invokes `training-sync --fetch DATE`, `training-sync --weight DATE`, or passes a positional JSON workout
- **THEN** the CLI exits with an argument error
- **AND** the error does not perform Garmin, vault, or Weight x Reps writes

#### Scenario: Strength import replacement
- **WHEN** the user needs to import a strength workout JSON document
- **THEN** the supported command is `training-sync garmin import-strength FILE`

### Requirement: Synchronization behavior is preserved
The identity cutover MUST NOT weaken or alter the existing synchronization safety contracts for Garmin, Obsidian, or Weight x Reps.

#### Scenario: Complete test suite after namespace migration
- **WHEN** the namespace and CLI migration is complete
- **THEN** all existing non-legacy behavior tests pass under the installed `training-sync` distribution
- **AND** every Garmin activity and preserved strength activity for a requested day retains its existing handling

#### Scenario: Remote write verification remains mandatory
- **WHEN** a Training Sync command writes a reconciled Weight x Reps day
- **THEN** it reports success only after the saved fields are read back and verified according to the existing specifications

#### Scenario: Existing daily-note safety remains mandatory
- **WHEN** a synchronization targets a date without the required existing daily note or encounters ambiguous exercise resolution
- **THEN** the command retains its existing stop-before-write behavior

### Requirement: Existing Training Sync configuration is preserved
The migrated project SHALL continue using `~/.config/training-sync/` for Garmin tokens, Weight x Reps tokens, exercise mappings, and the Weight x Reps user id without requiring secret migration.

#### Scenario: Configuration path resolution
- **WHEN** the migrated package resolves any supported local configuration file
- **THEN** it resolves the same file under `~/.config/training-sync/` as before the cutover

#### Scenario: Cutover does not rewrite credentials
- **WHEN** the project identity and checkout are migrated
- **THEN** credential and token contents are not printed, copied, or rewritten as part of the migration

### Requirement: Live operational references use the canonical identity
Current operational documentation and known local automation SHALL use the `training-sync` command and `/Volumes/ssd1/dev/training-sync` checkout after the machine cutover.

#### Scenario: Current repository documentation
- **WHEN** a user follows the README installation and usage instructions
- **THEN** every current command and source path uses the canonical Training Sync identity

#### Scenario: Known personal automation references
- **WHEN** the machine cutover is completed
- **THEN** the Codex project configuration and Garmin-to-Obsidian training skill point to `/Volumes/ssd1/dev/training-sync`
- **AND** the skill invokes only modern `training-sync` commands

#### Scenario: Historical records remain unchanged
- **WHEN** a legacy name appears only in an archived OpenSpec change, retrospective, or historical Superpowers artifact
- **THEN** the migration does not require rewriting that historical reference

### Requirement: Cutover is verified from an installed environment
The migration SHALL be considered complete only after repository verification and machine-level cutover checks pass from the canonical checkout.

#### Scenario: Repository verification gate
- **WHEN** implementation is ready for machine cutover
- **THEN** the full test suite passes
- **AND** a clean temporary installation exposes the `training-sync` distribution and command only
- **AND** packaged Garmin exercise data can be loaded from the installed package

#### Scenario: Final machine cutover
- **WHEN** `/Volumes/ssd1/dev/garmin-sync` is renamed to `/Volumes/ssd1/dev/training-sync`
- **THEN** the editable installation is recreated from the new path
- **AND** pyenv command resolution points to the new installation
- **AND** `training-sync --help` succeeds
- **AND** the obsolete `garmin-sync` command is absent

#### Scenario: Read-only integration smoke test
- **WHEN** final local verification is performed with valid existing credentials
- **THEN** at least one non-mutating Garmin command runs through the migrated package
- **AND** no mutating synchronization is required to prove the identity cutover
