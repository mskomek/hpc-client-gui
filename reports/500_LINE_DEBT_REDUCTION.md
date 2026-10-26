# 500-Line Debt Reduction

Date: 2026-10-23

## Result

Status: PASS for the repository architecture gate, with 39 existing over-limit allowlisted files remaining.

The current checker passes over 868 first-party files. No unallowlisted over-limit file is reported. The allowlist was reduced from 49 to 42 entries earlier in this continuation, then the 1,192-line `tests/test_plugin_manager_ui.py` was split by responsibility into refresh/status, install/update/remove, discovery/compatibility, and installed-version/rollback modules. Its 37 tests passed before and after the split.

The 545-line `tests/test_wave0_unicode_baseline.py` also contained a cohesive static encoding-boundary inventory. That class now lives in `tests/test_encoding_boundary_inventory.py`; the baseline module is 462 lines and its allowlist entry is removed. Unicode baseline, encoding inventory, release-gate, and files-output tests passed 103/103 after the extraction. A broader selection of eight relevant modules passed 155/155 in 84.58 seconds. Ruff and the line-limit architecture check pass.

The allowlist is now 39 entries: 27 independent of the other dirty checkout and 12 cross-checkout conflict files, which remain untouched. This continuation also split remote clipboard GUI coverage from `tests/test_wx_remote_file_actions_behavior.py`; the original is now 445 lines, and the clipboard actions live in `tests/test_wx_remote_clipboard_actions.py` with a shared wx fixture/builder. The system clipboard writer is a small service with bounded retry and guaranteed close semantics; its adapter tests and the related wx action/context tests passed 42/42. The 400–500 line warning zone remains. The SSH retry policy was also extracted into a cohesive helper, keeping `ssh/client.py` below the hard limit at 496 lines. Journal Studio's large-file visual refresh pauses structure rendering beyond 10,000 lines while retaining journal text.

The 12 conflicted files overlap changes in the separate user checkout on `codex/log-repeat-groups`. That checkout was not modified. No new exception was added to hide debt.

The extractions are not committed. No import-cycle checker exists in the repository scripts; the extracted test support modules depend only on their test layer and lower-level plugin contract/data, and `compileall` passed for the touched test files.

Evidence: `tests/test_plugin_manager_ui.py` at application HEAD was run as `.tmp/test_plugin_manager_ui_baseline.py` (37 passed). The four extracted modules then passed 37/37. The encoding extraction's focused group passed 103/103; the broader selection passed 155/155. The clipboard and related GUI action selection passed 42/42 after extraction. Ruff passed, and `scripts/check_line_limits.py` passed with 39 exceptions.

## 2026-10-24 continuation

`src/hpc_gui/config/storage.py` was split by responsibility into `storage_io.py`, `profiles_store.py`, `settings_store.py`, and `window_state.py`, retaining `storage.py` as the public facade. This removes one allowlist exception. The same focused Windows11 VM selection passed 37 tests with 2 skips before and after the extraction; Ruff and `compileall` passed. The architecture gate now scans 872 first-party files and passes with **38 allowlisted exceptions**: 26 independent candidates plus 12 cross-checkout conflicts. The 12 conflicted files remain untouched. Frozen current-source GUI and CLI archive listings include all four storage implementation modules. Evidence is recorded in `reports/F08_ARCHITECTURE_DEBT.md` and `.tmp/f08-storage-focused-windows11-result.json`.

## 2026-10-25 fix4 snapshot gate recheck

`scripts/check_line_limits.py` passed with exit 0 against the worktree used for source snapshot ZIP SHA-256 `642e080dae9254ecfcac658da83f9a658e3029b1acee3c3a29fa5be3e90579c7`, based on HEAD `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`: 877 first-party files scanned, 37 allowlisted over-limit files, and no unallowlisted violation. The 37 consist of 25 independent candidates plus 12 protected-checkout overlaps. No exception was added or removed; the source architecture gate is PASS while debt reduction remains PARTIAL.

## 2026-10-26 exact R5 architecture gate recheck

Repository `scripts/check_line_limits.py` passed against the worktree used for R5 source ZIP SHA-256 `A27B1970D19123A181523AB969AAAB3AF795FC419A8B481110E86B43D529B19C` and manifest SHA-256 `65E83A5E713E129F4BDFA2623476B07C740AD280AB4B3880E85174CEB3D414F3`. It scanned 881 first-party files and found 35 allowlisted over-500-line files with no unallowlisted violations. The 35 comprise 23 independent candidates and 12 files overlapping the protected `codex/log-repeat-groups` checkout; the latter were not touched. The current gate is **PASS**, while debt retirement remains **PARTIAL**. Captured output SHA-256: `EC2E19C1D05270A37E716207930FEE7B3543630AFA9E64E4028B9C95B23DC08F`; evidence: `.tmp/F10-current-source-20261026/evidence/r5/line-limit-check-r5.log`.

## 2026-10-26 Jobs outputs test split

The 673-line wx Jobs/files/outputs test module was separated into 328-line job/files/basic-output coverage and 278-line output-channel/follower lifecycle coverage. A 40-line support module owns the shared fake backend and wx panel lifecycle helpers. The 16 focused tests passed on Windows11-New; the final R6c full pytest and three serial broad wx runs passed. The two moved tests' `gui`/`wx` markers were verified and restored before the final run.

The stale allowlist entry for the now-328-line original module was removed after focused validation. The repository gate passes across 883 first-party files with **34 exceptions** (22 independent plus 12 protected-checkout overlaps) and no unallowlisted violation. No conflicting file in the user's separate checkout was touched. Ruff and `git diff --check` passed. Final source ZIP SHA-256 `82744F9CBB16266E88613E883F7D9E24D59A37D4478BBFD36AC0EDD58FA0B9E5`; manifest SHA-256 `54F4280E4068045F0CE20A55C850AE76B4E07EB0C96479EAE53345DBAD71832E`; evidence is under `.tmp/F08-jobs-outputs-20261026/evidence/r6c/`. Architecture gate: **PASS**. Debt retirement: **PARTIAL**, with 34 exceptions still open.

## 2026-10-26 latest architecture gate after F08 splits

Following the Windows updater source extraction and SSH jump-host profile test split, `scripts/check_line_limits.py` passes across **893 first-party files** with **29 allowlisted over-500-line files**: **17 independent candidates** and **12 protected-checkout overlaps**. No unallowlisted violations were reported. The SSH jump-host split removed one stale exception after the pre-split 24-test baseline and post-split 24-test Windows11-New focused run both passed. Ruff and `git diff --check` pass for the touched modules. The final layered full regression R5 passed 4,415 tests and skipped 50; it is recorded separately and is not added to other suite counts. Evidence: `.tmp/F08-jobs-scroll-20261026/evidence/local/line-limit-after-ssh-jump-profile-split.log`, `ruff-ssh-jump-profile-split.log`, and `kole-win11-new/full-interactive-r5.result.json`.
