# WAVE 04 — Config Storage

Status: **WAVE_COMPLETE** on the isolated integration branch. `develop` remains unchanged.

## Source identity

- Wave start: `66f07565e19947b8140c5f7798fa32c2b3e36890`.
- Source commit: `71ef960bb486cc821e1a79f969e5b58913841715` (`refactor(config): integrate modular storage facade`).
- Source tree: `7e9ade7db80efb0a186a16a45c7c1660074c3f6f`.
- Jobs source: `713949fb752b90601e007812ebf2bd765da5ad52`; there was no Jobs config-storage delta to select.
- V2 source: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`; selected modular storage implementation from `79fec477`.
- Changed-file fingerprint: `c41c0f9b5873f2e0ee49c5420d1bb3fd2f4aa63aa885c7073c226f2b74c6f153`, SHA-256 over sorted `path + NUL + SHA256(committed blob bytes) + newline` records for the 27 changed Python files.

The V2 dirty snapshot remains untouched. Its core file had raw fingerprint `9dd15527e6b4fe6925d5b12534980ad6cc5318b38c7b0ad8fb8547668d62baba`; that WIP added `sys.modules` callbacks from core back into the facade and was not copied because it creates a hidden reverse dependency. The profile WIP fingerprint was `a461f70df7857a96ca4cf1340be2f43c7125f1fb48fe72acd954e1661c3c0ef3`; its one-way core-module indirection was implemented explicitly instead. Profile deletion cleanup remains composed at the public facade so the extracted profile module does not add a new service dependency cycle.

## Changes and compatibility

- Replaced the 832-line storage module with a 233-line public facade and four cohesive modules: `_storage_core.py`, `_storage_preferences.py`, `_storage_profiles.py`, and `_storage_window_state.py`.
- Restored two develop settings missing from the V2 facade: `get_hide_finished_jobs_enabled` / `set_hide_finished_jobs_enabled` and `get_ssh_connection_attempts` / `set_ssh_connection_attempts`. SSH attempts remain bounded to 1–5, defaulting to 5.
- The facade exports 93 names; the committed-source check found no missing runtime exports. `app_data_dir` remains available for compatibility, while core path resolution reads the canonical `hpc_gui.core.paths` module.
- Kept atomic config writes, corruption backup, pre-migration backup, stable profile IDs, legacy parallelism migration, unknown profile fields, CLI access settings, FTP preferences, file associations, sbatch modes, and window-state validation in their original responsibilities.
- Updated config tests to patch the canonical core path/write functions. The sbatch preference facade retains callback injection so existing public `load_settings` and `update_settings` patch seams continue to work.

## Physical line counts

Counts include blank lines, comments, and docstrings. New Python files start at zero.

| Python file | Start | End |
|---|---:|---:|
| `src/hpc_gui/config/storage.py` | 832 | 233 |
| `src/hpc_gui/config/_storage_core.py` | 0 | 174 |
| `src/hpc_gui/config/_storage_preferences.py` | 0 | 406 |
| `src/hpc_gui/config/_storage_profiles.py` | 0 | 130 |
| `src/hpc_gui/config/_storage_window_state.py` | 0 | 127 |
| `tests/_cli_access_settings.py` | 286 | 286 |
| `tests/_cli_profile_commands.py` | 484 | 484 |
| `tests/_cli_test_support.py` | 61 | 61 |
| `tests/test_config_storage_atomic.py` | 38 | 38 |
| `tests/test_file_open_service.py` | 265 | 265 |
| `tests/test_jobs_history.py` | 115 | 115 |
| `tests/test_live_tracking_settings.py` | 17 | 17 |
| `tests/test_lssrv_auto_refresh.py` | 317 | 317 |
| `tests/test_security_hardening_wave.py` | 186 | 186 |
| `tests/test_ssh_connection_retry.py` | 77 | 76 |
| `tests/test_transfer_parallelism_migration.py` | 159 | 159 |
| `tests/test_w03_settings_provider_inventory.py` | 357 | 357 |
| `tests/test_w25_transfer_workspace_integrity.py` | 475 | 475 |
| `tests/test_w28_jobs_identity_refresh.py` | 480 | 480 |
| `tests/test_w37_settings_persistence.py` | 421 | 422 |
| `tests/test_w37_settings_plugin_gui.py` | 249 | 249 |
| `tests/test_w38_migration_secrets.py` | 347 | 347 |
| `tests/test_w40_gui_acceptance.py` | 258 | 258 |
| `tests/test_w40_localization_window_settings.py` | 334 | 334 |
| `tests/test_wave10_release_gate.py` | 297 | 297 |
| `tests/test_wave37_diagnostics.py` | 41 | 41 |
| `tests/test_wx_migration.py` | 108 | 108 |

All 27 changed Python files are at or below 500 lines. The shared changed-source gate reports five files in the 400–500 warning zone; the 406-line preferences module keeps one clear settings-persistence responsibility. The global inventory decreased from 51 to 50 files over 500 lines because `storage.py` is now below the limit. No exception was added.

## Verification on source commit `71ef960b`

| Check | Result | Exit | Evidence |
|---|---|---:|---|
| Focused config, profiles, migration, CLI, Jobs history and SSH suites | 356 passed, 0 failed, 1 skipped | 0 | `.tmp/wave04-config-tests-skip-reasons-20261021T180207137.log` |
| Skip classification | `test_security_hardening_wave.py:176` skipped: POSIX permission semantics on Windows | — | same pytest log |
| wx settings and window-state suites | 27 passed, 0 failed, 0 skipped | 0 | `.tmp/wave04-wx-settings-committed-20261021T180318451.log` |
| FTP sbatch-follow preference regression | 1 passed; 167 tests deselected by the focused selector | 0 | `.tmp/wave04-ftp-follow-committed-20261021T180318688.log` |
| Compatibility spot rerun | 38 passed, 0 failed, 0 skipped | 0 | `.tmp/wave04-restored-target-tests-20261021T180026689.log` |
| Ruff on changed Python files | passed | 0 | committed-source command output |
| `compileall` on `src/hpc_gui/config` | passed | 0 | committed-source command output |
| Facade export check | 93 declared names, 0 missing | 0 | committed-source command output with `src` on `sys.path` |
| Changed-source architecture gate, base `66f07565...` | PASS; 822 Python files scanned, no new LOC/import/cycle/API errors | 0 | `.tmp/wave04-architecture-committed-20261021T180318694.json` and `.md` |

The initial broad run exposed one test that still patched `storage.save_config`; it was retargeted to the canonical core write function, then the full focused suite passed. This was a test patch-point mismatch, not an unresolved product failure. The one POSIX-only test is recorded as a skip, not a pass.

GitHub Actions were not run. Full release acceptance, native Windows11 guest acceptance, and Ubuntu/Linux package acceptance remain pending WAVE 12. Global architecture debt remains at 50 over-limit files, 2 inherited unresolved imports, and 8 inherited dependency cycles; the changed-source gate reports 0 new instances and 0 public API errors.

## Integration state

The source commit is complete on `codex/integration/v2-jobs-staged-20261021`. It has not been merged to local `develop`; that branch remains checked out in a separate worktree. No remote mutation was made.
