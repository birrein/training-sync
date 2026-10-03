## Context

Garmin support in Training Sync lives in `src/training_sync/garmin/`, with `get_client()` providing the existing authenticated `Garmin` instance and argparse commands in `cli.py`. `garminconnect` exposes authenticated GET helpers and a generic client `put`. The Nutrition service is unofficial: the verified food-log contract is PUT `/nutrition-service/food/logs` with `mealDate` and `foodLogItems`, followed by GET `/nutrition-service/food/logs/{date}`. A third-party implementation and mocked contract tests corroborate the shape; the user's account successfully accepted the request and GET read-back verified it.

## Goals / Non-Goals

**Goals:** reusable, explicit CLI logging; exact food/serving resolution; local-time meal assignment; safe duplicate and uncertain-write handling; verified read-back.

**Non-Goals:** food-database editing/creation, nutrient estimation, meal planning, syncing external nutrition services, or tests that write to a real Garmin account.

## Decisions

- Put request construction, food matching, meal selection, duplicate detection and reconciliation in `training_sync.garmin.nutrition`; keep CLI parsing/printing in `cli.py`.
- Accept explicit date/time and repeated food-plus-quantity inputs. Prefer exact foods and servings in Garmin's daily serving list, then resolve from food search using exact normalized names; support metric mass conversion and exact catalog servings, and stop on ties or incompatible units.
- Use `regionCode`/`languageCode` and food `source` from the matched Garmin catalog item. Do not hardcode US/en.
- Select exactly one enabled meal by its returned time window, including windows that cross midnight. When no configured window matches, use the unique enabled `SNACKS` meal only if Garmin leaves its window unset; otherwise fail closed. This matches the account's verified meal setup, where afternoon entries use `SNACKS`.
- Before mutation, read the date log and detect an exact duplicate. Submit the entire batch once through the authenticated `client.put(..., api=True)` transport. Regardless of response, reconcile with GET; never auto-retry an uncertain write.
- Keep the unofficial path and payload inside the adapter. Treat upstream behavior as unstable and fail closed when expected response fields are missing.

## Risks / Trade-offs

- Garmin's private API may change → centralize its contract and cover request/response handling with fixtures and mocked tests.
- Catalog search can be ambiguous or unit representations inconsistent → require a unique exact food and compatible serving; print candidates rather than guessing.
- The write may partially apply or its response may be lost → read back each expected item and report unresolved state without retrying.
- Meal times can cross midnight or overlap → compare normalized local time windows, including overnight windows, and require exactly one enabled match.

## Migration Plan

No data migration or dependency change. Add the command and adapter; existing Garmin commands and stored sessions remain unchanged.
