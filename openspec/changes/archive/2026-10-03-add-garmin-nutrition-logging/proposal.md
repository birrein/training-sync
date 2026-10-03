## Why

Training Sync can already read Garmin nutrition but has no safe reusable way to record food. Users need explicit portion and local meal time logging with the same read-back guarantees as other Garmin writes.

## What Changes

- Add a focused Garmin food-log command that resolves catalog foods and serving sizes, preserves existing entries, prevents duplicate writes, and verifies saved entries.
- Keep the unofficial Garmin Nutrition API contract inside a dedicated adapter.

## Capabilities

### New Capabilities
- `garmin-nutrition-logging`: Find and log selected foods by serving and local meal time with duplicate protection and verified results.

### Modified Capabilities
- None.

## Impact

Adds a Garmin nutrition adapter and CLI command using the existing Garmin session and `garminconnect` transport. No new dependency or credential is needed.
