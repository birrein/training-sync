## Cutover Evidence

Cutover completed on 2026-07-21 in the `America/Santiago` timezone.

- Repository branch: `refactor/project-training-sync-cutover`.
- Repository migration commits before the machine cutover: `707cbaa` and `fc5ae7f`.
- Canonical checkout: `/Volumes/ssd1/dev/training-sync`.
- Obsolete checkout `/Volumes/ssd1/dev/garmin-sync`: absent after the validated rename.
- Codex project trust and open-in preferences: updated to the canonical checkout and parsed successfully as TOML.
- Personal Garmin-to-Obsidian skill: reference-tested before and after editing; it now uses the canonical checkout and modern `training-sync garmin` commands.
- Global pyenv, `venv`, and uv-managed `.venv`: each exposes the `training-sync` 1.0.0 distribution and `training-sync` console script from the canonical checkout.
- Legacy `garmin-sync` distribution, `garmin_sync` import, console entry point, and pyenv shim: absent in all verified environments.
- Runtime configuration: continues to resolve under `~/.config/training-sync/`; file existence was checked without reading or printing credential contents.
- Full suite after the physical rename and reinstall: 221 tests passed.
- Read-only Garmin smoke test: `training-sync garmin fetch 2026-07-15` authenticated with the existing token and returned the recorded activity without writing data.
- No mutating Garmin, Obsidian, or Weight x Reps synchronization was used for cutover verification.

## Rollback

If the cutover must be reversed:

1. Stop work in the canonical checkout and ensure there are no uncommitted changes.
2. Switch to the pre-migration `main` branch, which still contains the former project identity.
3. Rename `/Volumes/ssd1/dev/training-sync` back to `/Volumes/ssd1/dev/garmin-sync` after confirming the destination is absent.
4. Restore the two Codex configuration keys and the Garmin-to-Obsidian skill commands/path to the former checkout.
5. Uninstall `training-sync`, reinstall the old checkout in editable mode in the global pyenv environment and any retained virtual environments, and run `pyenv rehash`.
6. Verify the previous command help and run a read-only Garmin fetch before resuming normal use.

The rollback does not move or rewrite `~/.config/training-sync/` tokens, mappings, or user-id state, and it does not alter vault notes or remote training records.
