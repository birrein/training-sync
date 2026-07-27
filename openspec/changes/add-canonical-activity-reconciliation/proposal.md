## Why

Training Sync now coordinates completed activity data across Garmin, the Obsidian vault, Weight x Reps, and manually synchronized Intervals.icu activities, but its shared models and synchronization flow still expose provider-specific representations. Adding more lifecycle operations directly to each client would duplicate matching, confirmation, partial-failure, and verification rules just as TrainingPeaks and additional Garmin or vault operations become relevant.

## What Changes

- Introduce a provider-neutral canonical training model for completed activities, strength imports, exercises, sets, scoped effort observations, provenance, and remote replicas.
- Replace the Weight x Reps-centered exercise identity with a stable local exercise catalog and provider-specific mappings.
- Introduce scoped reconciliation that can target one platform, an explicit subset, or every configured destination without modifying unselected platforms.
- Generate a complete preview before mutation, require explicit authorization to apply it, and verify each target independently by read-back.
- Add Intervals.icu activity read, create, update, and delete behavior with deterministic duplicate detection and guarded deletion.
- Preserve the user's current Fitbod screenshot to verified Garmin to downstream synchronization flow, including the intended subscription period through 2027-01-11, without encoding that date as product behavior.
- Preserve existing Garmin, vault, and Weight x Reps user-visible behavior while moving their representations behind provider adapters.
- Keep TrainingPeaks integration and new Garmin or vault lifecycle operations out of this change; they will use the same seams in later changes after their concrete capabilities and use cases are confirmed.

## Capabilities

### New Capabilities

- `canonical-training-model`: Provider-neutral completed activity and strength representations, authority and provenance rules, stable exercise identity, scoped effort observations, and remote replica identity.
- `scoped-activity-reconciliation`: Exact target selection, deterministic planning, preview and authorization, capability-aware application, conflict handling, partial results, and independent read-back verification.
- `intervals-activity-crud`: Safe Intervals.icu activity inventory, matching, creation, update, deletion, and post-mutation verification.

### Modified Capabilities

None. Existing daily, Weight x Reps, and project-identity requirements remain behaviorally unchanged.

## Impact

- Affected modules include the current Garmin activity model, Weight x Reps parser and renderer models, exercise mapping and resolution, the one-day synchronization use case, CLI composition, and provider configuration.
- A new Intervals.icu adapter and focused CLI operations will be added.
- Existing Garmin, vault, and Weight x Reps adapters will be migrated to the canonical model without changing their current safety contracts.
- No database, background synchronization process, TrainingPeaks dependency, or automatic mutation of every configured platform is introduced.
