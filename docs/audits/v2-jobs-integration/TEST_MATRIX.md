# Test Matrix

## Local evidence

| Check | Command / source | Result | Exit |
|---|---|---:|---:|
| Architecture gate unit tests | `D:\Projeler\hpc-client-gui\.venv\Scripts\python.exe -m pytest tests/test_source_architecture_gate.py -q` | 5 passed | 0 |
| Architecture gate Ruff | `python -m ruff check scripts/check_source_architecture.py tests/test_source_architecture_gate.py` | passed | 0 |
| Architecture gate syntax | `python -m py_compile scripts/check_source_architecture.py tests/test_source_architecture_gate.py` | passed | 0 |
| Changed-source architecture gate | shared Agent Core + project gate, base `f61919bad12be5f328cb9db3fee3c8de8563fa5b` | PASS; 52 untouched baseline files remain over limit; no new errors | 0 |
| Starting full architecture inventory | shared Agent Core `--scope project` at starting SHA | FAIL as expected for baseline debt: 52 over limit | 1 |
| Full architecture on WAVE 00 working tree | shared Agent Core `project` + project dependency/API/cycle gate | FAIL as expected: 52 over limit, 2 inherited symbol imports, 8 inherited cycles, 0 API errors | 1 |
| Wave 01 Jobs persistence/history | five focused Jobs service suites at `c1d8e66f5b5b4a06abcf79511c48bf97017df0cf` | 45 passed, 0 failed, 0 skipped | 0 |
| Wave 01 Ruff | Ruff over all 11 changed Python files | passed | 0 |
| Wave 01 compileall | six Jobs service modules | passed | 0 |
| Wave 01 changed-source architecture gate | base `179fb47dfc94765cbec5d9eb058ba0d0f6247232`, 782 Python files | PASS; no new LOC/import/API/cycle errors; 52 existing over-limit files remain | 0 |
| Wave 01 full project architecture | `--mode full` at `c1d8e66f5b5b4a06abcf79511c48bf97017df0cf` | FAIL expected: 52 LOC violations, 2 unresolved imports, 8 cycles, 0 API errors | 1 |
| Wave 02 Jobs controllers/workspace/history | 11 focused suites at `d12a752c1557b2cff7ea5a21bbf2d391c13b5fa3` | 95 passed, 0 failed, 0 skipped | 0 |
| Wave 02 extended wx Jobs regressions | Files/Outputs, Details, corrective Details, Jobs stress, auto refresh, history dashboard | 64 passed, 0 failed; exit 0; shutdown emitted wx `UnregisterClass` 0x584 before fixture correction | 0 |
| Wave 02 post-fix teardown stress | `tests/test_wx_jobs_stress.py` after shared-App cleanup fix | 10 passed, no teardown warning | 0 |
| Wave 02 post-fix window handoff | Files tab case followed by rapid-selection stress case in one process | 2 passed, no teardown warning | 0 |
| Wave 02 compatibility | `tests/test_w13_slurm_state.py` | 14 passed; `_parse_job_row` import remains available | 0 |
| Wave 02 architecture gate tests | `tests/test_source_architecture_gate.py` | 6 passed | 0 |
| Wave 02 Ruff and compileall | changed Jobs/controller/helper implementation files | passed | 0 |
| Wave 02 changed-source architecture gate | base `7c3ee2260aac03eea2e6aebf7d9f3e7a39ee55e3`, 817 Python files | PASS; 51 untouched over-limit files remain; no new import/API/cycle errors | 0 |
| Wave 02 full project architecture | `--mode full` at `d12a752c1557b2cff7ea5a21bbf2d391c13b5fa3` | FAIL expected: 51 LOC violations, 2 unresolved imports, 8 cycles, 0 API errors | 1 |
| Wave 03 release runner | `python -m pytest tests/test_release_test_suite.py -q` at `4ed2075c072b0cd38ca05249a9670aa96dfc3af1` | 13 passed, 0 failed, 0 skipped | 0 |
| Wave 03 Ruff | `python -m ruff check scripts/release_test_suite.py scripts/native_gui_test_files.py scripts/ci.py tests/test_release_test_suite.py` | passed | 0 |
| Wave 03 compileall | `python -m compileall -q scripts/release_test_suite.py scripts/native_gui_test_files.py scripts/ci.py tests/test_release_test_suite.py` | passed | 0 |
| Wave 03 evidence hash | `_evidence_failures()` against the committed W04 support matrix | no evidence failures; raw file SHA-256 matches the pinned digest | 0 |
| Wave 03 wheel build | `python -m build --wheel --outdir <temporary .tmp directory> <repository>` | wheel built successfully; non-fatal setuptools license-format deprecation warning | 0 |
| Wave 03 changed-source architecture | `--mode gate --base 49ce32cc85d9a926542597b33f70dec259e7e2e1` at WAVE 03 source | PASS; 818 Python files scanned, no new LOC/import/cycle/API errors | 0 |
| Wave 03 full project architecture | `--mode full` at `4ed2075c072b0cd38ca05249a9670aa96dfc3af1` | FAIL baseline debt: 51 LOC violations, 2 unresolved imports, 8 cycles, 0 API errors | 1 |
| Wave 04 config/profile/CLI/Jobs-history/SSH regressions | `python -m pytest -q -rs` over 21 focused modules at `71ef960bb486cc821e1a79f969e5b58913841715` | 356 passed, 0 failed, 1 skipped (`test_security_hardening_wave.py:176`, POSIX permission semantics) | 0 |
| Wave 04 wx settings/window state | `tests/test_w37_settings_plugin_gui.py tests/test_w40_localization_window_settings.py` at `71ef960bb486cc821e1a79f969e5b58913841715` | 27 passed, 0 failed, 0 skipped | 0 |
| Wave 04 FTP sbatch-follow setting | `tests/test_ftp_widget.py -k sbatch_follow_mode_settings_migrate_and_persist` at `71ef960bb486cc821e1a79f969e5b58913841715` | 1 passed; 167 deselected by the explicit focused selector | 0 |
| Wave 04 compatibility spot rerun | storage-path, migration-write, atomic config, profile, provider, and SSH retry selections at `71ef960bb486cc821e1a79f969e5b58913841715` | 38 passed, 0 failed, 0 skipped | 0 |
| Wave 04 Ruff and compileall | Ruff on changed Python files; `python -m compileall -q src/hpc_gui/config` | passed | 0 |
| Wave 04 facade API check | committed facade imported with `src` on `sys.path` | 93 declared exports, 0 missing runtime names | 0 |
| Wave 04 changed-source architecture | `--mode gate --base 66f07565e19947b8140c5f7798fa32c2b3e36890` at `71ef960bb486cc821e1a79f969e5b58913841715` | PASS; 822 Python files, 50 global over-limit files, 0 new dependency/import/cycle/API errors | 0 |
| Wave 05 auth/profile/SSH/CLI/SFTP regressions | `.venv` pytest batch at `b7e6cac89cc8f2efa48c0a4cbbbfbfe834ea8825` | 139 passed, 0 failed, 0 skipped; 9 subtests passed | 0 |
| Wave 05 wx connection/profile/security/lifecycle regressions | `.venv` pytest batch with `load_language('en')` before pytest at `b7e6cac89cc8f2efa48c0a4cbbbfbfe834ea8825` | 87 passed, 0 failed, 0 skipped | 0 |
| Wave 05 locale precondition diagnosis | `test_selected_vs_active_profile` at `b7e6cac89cc8f2efa48c0a4cbbbfbfe834ea8825` | Without locale initialization: fallback translation keys caused 1 test failure; with English loaded: 1 passed; full locale-initialized batch passed 87/87 | 0 on controlled reruns |
| Wave 05 Ruff and compileall | Ruff over all 13 changed Python files; compileall over changed application modules at `b7e6cac89cc8f2efa48c0a4cbbbfbfe834ea8825` | passed | 0 |
| Wave 05 changed-source architecture | `--mode gate --base fabc11b01b517f53c55ebf882972c6529a441a9f` at `b7e6cac89cc8f2efa48c0a4cbbbfbfe834ea8825` | PASS; 831 Python files, 48 global over-limit files, 0 new import/cycle/API errors | 0 |
| Wave 06 CLI regressions | `python -m pytest -q -rs tests/test_cli.py tests/test_cli_entrypoint.py tests/test_cli_saved_credentials.py tests/test_cli_terminal_output.py` at `7675422c1d077572f96ff4fad1b8c703d53ffb31` | 177 passed, 0 failed, 0 skipped | 0 |
| Wave 06 Ruff and compileall | Ruff over 17 changed Python files; `python -m compileall -q src/hpc_gui/cli` at `7675422c1d077572f96ff4fad1b8c703d53ffb31` | passed | 0 |
| Wave 06 facade API check | AST public-symbol comparison between the pre-refactor CLI facade and `main.py` at `7675422c1d077572f96ff4fad1b8c703d53ffb31` | no public symbols missing | 0 |
| Wave 06 changed-source architecture | `--mode gate --base 2d08506d85bc287b21c92c2e28e4e81bfa1b4efb` at `7675422c1d077572f96ff4fad1b8c703d53ffb31` | PASS; 839 Python files, 47 global over-limit files, 0 new dependency/cycle/API errors | 0 |
| Wave 07 plugin/installer/menu/schema/security batch without external contract checkout | plugin test files plus UI contribution, hardening, lifecycle, provider, and docs-contract suites at `ce598c2859b31d0abdfaaf6c071a6898eec60782` | 450 passed, 0 failed, 40 skipped (39 external-checkout path skips, 1 POSIX-only permission test) | 0 |
| Wave 07 cross-repository plugin contracts | `tests/test_plugin_contract.py tests/test_plugin_contract_fluent_compatibility.py tests/test_plugin_v2_integration.py tests/test_w09_main_plugin_compat.py` with `HPC_GUI_CONTRACT_REPO=D:\Projeler\hpc-client-gui-plugins` at `ce598c2859b31d0abdfaaf6c071a6898eec60782` | 30 passed, 0 failed, 0 skipped | 0 |
| Wave 07 Fluent plugin integration | `tests/test_fluent_plugin_integration.py` with a temporary collection hook pointing at the local checkout at `ce598c2859b31d0abdfaaf6c071a6898eec60782` | 9 passed; assertions unchanged | 0 |
| Wave 07 contract-enabled broad plugin batch | Same broad plugin batch with the local contract checkout | 479 passed; one wx menu subprocess timed out at its existing 15-second limit; 10 skipped; isolated rerun of the timed-out case passed | 1 for broad batch, 0 for isolated rerun |
| Wave 07 Ruff and compileall | Ruff and compileall over all 19 changed Python files at `ce598c2859b31d0abdfaaf6c071a6898eec60782` | passed | 0 |
| Wave 07 facade API check | `validator.py` and `ui_contributions.py` compared against `3efd890b` | no previous public symbols missing; all explicit facade exports exist at runtime | 0 |
| Wave 07 changed-source architecture | `--mode gate --base 3efd890b5deb1ccf36e423d3000fa1b75f1481d0` at `ce598c2859b31d0abdfaaf6c071a6898eec60782` | PASS; 853 Python files, 42 global over-limit files, 0 new dependency/cycle/API errors | 0 |
| Wave 08 Qt Jobs Outputs regression batch | focused scroll, output selection, live tracking, WAVE 80, context menu, and W29 suites at `abe774525cf93b4f20c810b70e8e19fa7585d762` | 97 passed, 0 failed, 0 skipped; 4 subtests passed | 0 |
| Wave 08 Ruff and compileall | Ruff and compileall over all 19 changed Python files at `abe774525cf93b4f20c810b70e8e19fa7585d762` | passed | 0 |
| Wave 08 facade compatibility | runtime `__all__` check plus AST method comparison at `abe774525cf93b4f20c810b70e8e19fa7585d762` | 72 exports present; all 58 pre-refactor widget methods retained | 0 |
| Wave 08 changed-source architecture | `--mode gate --base 7f340c3bd9122627deb9fa63b9e1d98e631065f0` at `abe774525cf93b4f20c810b70e8e19fa7585d762` | PASS; 867 Python files, 39 global over-limit files, 0 new dependency/API/cycle errors | 0 |
| Wave 09 updater and splash regressions | 8 focused updater/routing/splash modules at `4c8232a746643350f29affa8b6c621c1303364e2` | 89 passed, 0 failed, 0 skipped | 0 |
| Wave 09 FTP widget and dialog GUI regressions | `tests/test_ftp_widget.py` at `4c8232a746643350f29affa8b6c621c1303364e2` | 168 passed, 0 failed, 0 skipped; includes MainWindow-to-Jobs Outputs signal wiring and transfer dialogs | 0 |
| Wave 09 connection/settings/profile/template regressions | 8 focused connection, plugin-template and settings persistence modules at `4c8232a746643350f29affa8b6c621c1303364e2` | 101 passed, 0 failed, 0 skipped | 0 |
| Wave 09 transfer service and recovery regressions | 15 focused transfer, conflict, concurrency and local-gate modules at `4c8232a746643350f29affa8b6c621c1303364e2` | 96 passed, 0 failed, 0 skipped; 3 subtests passed | 0 |
| Wave 09 committed-source total | Four domain-separated batches above | 454 passed, 0 failed, 0 skipped; 3 subtests passed | 0 |
| Wave 09 Ruff and compileall | Ruff on the 27 changed Python files; `python -m compileall -q src/hpc_gui tests` at `4c8232a746643350f29affa8b6c621c1303364e2` | passed | 0 |
| Wave 09 public API compatibility | Runtime and AST comparison of connection/settings/transfer dialogs and module-level patch hooks | 29/29, 10/10 and 33/33 prior methods remain callable; all checked hooks remain available | 0 |
| Wave 09 changed-source architecture | `--mode gate --base 3b58c8f08a458d05b263ac9ffcd9daf9438291a0` at `4c8232a746643350f29affa8b6c621c1303364e2` | PASS; 887 Python files scanned, 33 global over-limit files, 1 inherited unresolved internal symbol import and 8 inherited cycles; no new LOC/dependency/API/cycle errors | 0 |
| Wave 09 mixed-domain exploratory run | One mixed updater/FTP/dialog pytest invocation while source edits were still in progress | Native Windows access violation `0xC000041D` at `tests/test_ftp_widget.py` teardown (`QApplication.processEvents()`); not bound to the committed source. Separate committed-source batches above passed; final release-runner isolation and GUI teardown checks remain required | `-1073740771` |
| Current develop sync regression | `python -m pytest -q tests/test_wx_logs_groups.py` at integration sync `1995d7f5cb28de5cdf34737f95202e9d4fb7af9b` | 10 passed, 0 failed | 0 |
| Current develop sync architecture gate | shared Agent Core + project gate, baseline `0aa8ce54321c9b5130bcf4366a88f8d731ac0898`, at integration sync `1995d7f5cb28de5cdf34737f95202e9d4fb7af9b` | PASS; 823 Python files, 50 LOC violations remain, 0 new import/API/cycle errors | 0 |
| Wave 10 FTP widget regression | 20 individual FTP test files, each launched in its own pytest process, at `4e5b698653538ceeadb7a2cd16ae593e942b18a4` | 168 passed, 0 failed, 0 skipped | 0 |
| Wave 10 adjacent Files/FTP regressions | 10 related directory listing, cache, sync, transfer-conflict and wx UI files, individually isolated, at `4e5b698653538ceeadb7a2cd16ae593e942b18a4` | 116 passed, 0 failed, 1 skipped (`test_synchronized_browsing.py`, POSIX-only behavior on Windows) | 0 |
| Wave 10 combined regression | Both isolated batches above | 284 passed, 0 failed, 1 platform skip; all 30 file processes exited 0 | 0 |
| Wave 10 compatibility and test preservation | Facade API probe and AST comparison for pre-split `test_ftp_widget.py` | All checked legacy methods/symbols and patch hooks remain; all 168 test functions retained with matching AST | 0 |
| Wave 10 Ruff and compileall | Ruff on changed FTP/panel/i18n/test sources; `python -m compileall -q src/hpc_gui tests` at `4e5b698653538ceeadb7a2cd16ae593e942b18a4` | passed | 0 |
| Wave 10 changed-source architecture | `--mode gate --base 3e648fbeae29cb2307bbc787288368ce478cb26a` at `4e5b698653538ceeadb7a2cd16ae593e942b18a4` | PASS; 937 Python files, 29 over-limit files; 0 new dependency/cycle/API errors | 0 |
| Wave 10 i18n | `python scripts/check_i18n.py` at WAVE 10 start and source commits | FAIL on both with the same 7 hardcoded strings and 3 missing keys in Jobs Outputs modules; inherited debt assigned to WAVE 11/12 | 1 |
| Full release acceptance suite | `python scripts/release_test_suite.py --scope acceptance` | NOT RUN; retained for WAVE 12 full acceptance | — |
| GitHub Actions | not run | NOT RUN | — |

The first `py -m pytest` attempt used the global Python 3.14 installation, which has no pytest module; the WAVE 00 suite was rerun with the project `.venv` and passed 5/5. During Wave 01 source selection, one exploratory suite invocation had 44 passes and one failure because a later Jobs Wave 02 test rewrite patched an extracted module not yet present. That test-only rewrite was excluded from Wave 01; the final WAVE 01 suites passed 45/45 with the existing test retained and provenance assertions added. This diagnostic failure is source incompatibility, not an unresolved product failure.

## Remaining acceptance blockers

All wave-focused suites are recorded above. Remaining release blockers are Ubuntu wxPython availability, unresolved Windows full-suite/SFTP/terminal-bridge results, release artifact validation, and hosted GitHub Actions. Unrun checks remain `NOT RUN`; skipped tests and environmental blockers are not counted as PASS. Local VM results and hosted CI are tracked separately.

## WAVE 11 VM evidence

| Area | VM command/check | Result | Exit | Classification |
|---|---|---:|---:|---|
| Architecture full gate | `scripts/check_source_architecture.py --mode full` on Ubuntu-Test r28 snapshot | 1,014 Python files, 0 over 500, 0 dependency errors, 0 cycles, 0 API errors | 0 | PASS |
| Architecture tests, Ruff, compileall, i18n | `pytest tests/test_source_architecture_gate.py -q`; Ruff `src scripts tests`; compileall; `scripts/check_i18n.py` | 7 passed; all quality checks passed | 0 | PASS |
| Windows focused wx/Qt/Jobs batch | Windows11 interactive r27 | 114 passed | 0 | PASS |
| Windows plugin manager dialog | Windows11 interactive r28, source manifest hash matched | 12 passed | 0 | PASS |
| Ubuntu portable release runner | Ubuntu-Test r28, `QT_QPA_PLATFORM=offscreen` | 2,639 passed, 206 skipped, 61 deselected, 29 subtests passed; no assertion failures; 101 wx-only isolated partitions exit 5 because `wx` is unavailable | 5 | BLOCKED_ENVIRONMENT; do not count runner as PASS |
| Windows portable release runner | Windows11 interactive r28 | Timed out after 2,700 seconds; exit -1; owned process tree stopped | -1 | BLOCKED_TIMEOUT |

The r28 source manifest fingerprint is `80a17499530c55331e684d984c9fe4971a9b534cb3ad5c2379195ef91329ad57`; manifest SHA-256 is `49c83e66f42317492d3d8705a2f84e0f971b1046e6a92545ee887f243c5da12e`. GitHub Actions has not run.

| Final architecture recheck | Ubuntu-Test VM snapshot r29; baseline deleted, global full mode | PASS: 1,015 Python files, 0 over limit, 0 dependency errors, 0 cycles, 0 API errors; shared LOC scan 1,041 files | 0 | PASS |
| Architecture regression rerun | `pytest -q tests/test_source_architecture_gate.py` on r29 | 7 passed | 0 | PASS |
| Ubuntu wheel packaging | `pytest -q --tb=short tests/test_wheel_packaging.py -m packaging` on r29 after installing missing `build` into VM venv | 1 passed, 3 deselected; wheel asset and dependency metadata assertions passed | 0 | PASS |
| Linux release package plan | `scripts/release_linux.py --json` on r29 | version 1.5.9 and AppImage/deb/Flatpak stages validated; dry run only | 0 | PASS (plan validation, no package artifact) |
| Ubuntu wheel test environment setup | First `pytest ... -m packaging` attempt before installing `build` | 1 failed because VM venv lacked executable `build.__main__`; no assertion failure | 1 | ENVIRONMENT; dependency installed and exact test rerun passed 1/1 |
| Qt editor under Xvfb/xcb | `tests/test_editor_flow.py` on Ubuntu-Test r28 | 3 focus assertions failed under the Xvfb/xcb backend; offscreen backend rerun passed 14/14 | 1 then 0 | DISPLAY/backend limitation; retained as a failed exploratory run, not counted as PASS |

## WAVE 12 VM evidence — source `f6eb59c0bf20d6f5dd3015a0f7bcb258c79fd913`

Source tree: `450c1d0ddb079122d5aa3efc90516bead03f0797`; source fingerprint: `bbfbbfad02d5d3b0a2ae7acd143c49ae62349b8136b1bf766c7bd85f729bdbef`.

| Area | VM command/run | Result | Exit | Classification |
|---|---|---:|---:|---|
| Global architecture | Ubuntu-Test r33, `scripts/check_source_architecture.py --mode full` | 1,015 files; 0 LOC, dependency, cycle, or API errors; shared LOC 1,041 entries / 0 over-limit | 0 | PASS |
| Quality gates | Ubuntu-Test r33, Ruff `src scripts tests tools`, compileall, i18n | All passed | 0 | PASS |
| Focused architecture/docs/Qt/provenance tests | Ubuntu-Test r33 | 41 passed | 0 | PASS |
| Final report docs references | Ubuntu-Test r30, after copying final reports | 2 passed; initial attempt failed before assertion because task PATH did not include bundled Git; exact rerun with `PATH`/`GIT_EXEC_PATH` configured passed | 0 (rerun) | PASS on rerun; environment failure recorded |
| Full acceptance runner | Ubuntu-Test r30, `scripts/release_test_suite.py --scope acceptance` | 2,639 passed, 0 failed assertions, 210 skipped, 61 deselected, 29 subtests passed; 105 wx-only partitions had no runnable tests | 5 | BLOCKED_ENVIRONMENT; not PASS |
| Ubuntu SFTP cancel/resume tests | Ubuntu-Test r30, `tests/test_download_cancel_wire.py` | 4 passed | 0 | PASS |
| Windows W15 startup/connection | Windows11 r33, `tests/test_w15_fresh_user_startup.py` | 11 passed | 0 | PASS |
| Windows full portable runner | Windows11 r28 run `7ad295fc24b14163adf32c241c49eed1` | 2,700-second timeout; partial results include 2 SFTP failures and 2 prior localization assertion failures; PowerShell/Git resolution errors | -1 | BLOCKED_TIMEOUT / ENVIRONMENT ERRORS |
| Windows focused terminal bridge | Windows11 run `e404c71b7f3c40069b7efb5d2d984006`; matching manifest SHA `72d5333de0d59dd6a5bc4f0d2e7036d359d8bb24a06d96acc516e8fd1315d86a` | 600-second timeout; stdout `.F`; pytest traceback and final summary absent; owned process tree stopped | -1 | BLOCKED_TIMEOUT; at least one failure marker, unresolved |
| Windows direct SFTP attempt | Windows11 isolated task | Did not collect because the task environment lacked PySide6 | 2 | BLOCKED_ENVIRONMENT; does not resolve the full-run failures |
| Ubuntu wheel packaging | Ubuntu-Test r30, packaging marker | 1 passed, 3 deselected | 0 | PASS |
| Linux package plan | Ubuntu-Test r30, release-plan dry run | AppImage/deb/Flatpak stages validated; no artifact built | 0 | PASS (plan only) |
| Windows/Linux release artifacts | Not run | No source-matched artifact produced | — | NOT RUN |
| GitHub Actions | Not run | No hosted workflow result | — | NOT RUN |

Windows terminal bridge host/guest hashes matched: `src/hpc_gui/wx_terminal_webview_bridge.py` `06cf09a766920819425555e5cc8fbafd0d40ad21c4b3aed9f6baa2d7e90585f7`, test `eedc26252adfc8b18a24bc8c2c665c2ed73d5949ab02b88f835b59048fe9f6af`, manifest `72d5333de0d59dd6a5bc4f0d2e7036d359d8bb24a06d96acc516e8fd1315d86a`. The Windows guest result is at `C:\Users\home\AppData\Local\CodexGuestRuns\e404c71b7f3c40069b7efb5d2d984006\result.json`; host runner trace and result are under `D:\Projeler\.tmp\hpc-client-gui\e404c71b7f3c40069b7efb5d2d984006.*`.

## VM reruns - 2026-10-22, source 78d233dc

| VM check | Result | Exit | Classification |
|---|---|---:|---|
| Ubuntu-Test full architecture after index correction | 1,015 Python files; 0 over-limit; 0 dependency, cycle, or API errors; shared LOC passed | 0 | PASS |
| Ubuntu-Test compileall, Ruff, i18n | All passed on the exact source archive | 0 each | PASS |
| Ubuntu-Test focused tests | App updater 18; transfer concurrency 10; download cancellation 4; architecture gate 7 | 0 each | PASS, 39 total |
| Ubuntu-Test SFTP wx proof | 1 skipped because wxPython is unavailable | 5 | BLOCKED_ENVIRONMENT; not PASS |
| Windows11 Jobs/SFTP/transfer | 24 passed on host/guest source-matched stage | 0 | PASS |
| Windows11 W15 startup/update | 11 passed on host/guest source-matched stage | 0 | PASS |
| Windows11 terminal bridge | Partial .F, 180-second timeout, owned process tree stopped | -1 | BLOCKED_TIMEOUT; unresolved |
| Windows11 architecture | compileall completed; architecture could not enumerate files in the first no-.git stage; synthetic-index retry failed before launch | 1 / no target exit | NOT VERIFIED on Windows; Ubuntu full gate is authoritative |

The corrected Ubuntu architecture JSON is ARCHITECTURE_FINAL.json. Commands, hashes, and the superseded 1,014-file report correction are in VM_RERUN_2026-10-22.md.


## r17 final VM acceptance — 2026-10-24

Source: base `48ac62334b398bbc95b4d14ca9ef23dc83c356f3` plus the verified 39-file overlay fingerprint `325593c807cab38278a93b45986f38ac3152c426421084780bc06ef99c201765`. The source identity manifest and archive hashes are recorded in WAVE 12.

| Check | Environment / command | Result | Exit |
|---|---|---:|---:|
| Full architecture | Kole Ubuntu-Test, Python 3.14.9, `scripts/check_source_architecture.py --mode full` | 1,020 Python files; 0 over 500 LOC; 0 dependency/API/cycle errors | 0 |
| Ruff | Ubuntu-Test and Windows11-New, Ruff 0.17.2 | passed | 0 |
| Full Linux release suite | Ubuntu-Test, `scripts/ci.py release` | 3,506 passed, 0 failed, 33 skipped, 46 deselected; 244 pytest child commands | 0 |
| Linux GUI and coverage | Ubuntu-Test under Xvfb/D-Bus, `scripts/ci.py gui` | 3,477 passed plus 29 subtests, 0 failed, 33 skipped, 46 deselected; coverage 69.56% / 65% floor | 0 |
| Windows release acceptance | Windows11-New, Python 3.14.7, `scripts/release_test_suite.py --scope acceptance` | 3,504 passed plus 29 subtests, 0 failed, 35 skipped, 46 deselected | 0 |
| Linux packages | Ubuntu-Test, `scripts/release_linux.py --version 1.5.9 --execute` | AppImage, Debian and Flatpak built; all sidecars and installed launcher `--help` smokes passed | 0 |
| Windows package | Windows11-New, isolated PyInstaller package run | GUI/CLI build and smoke, guide coverage, mocked transfer gate passed | 0 |
| GitHub Actions | Not run | No hosted result claimed | — |

The Linux and Windows counts describe separate, overlapping runs and are not summed as unique tests. The detailed logs, exit files, package manifests, artifact hashes, warnings, and cleanup probes are in `VM_ACCEPTANCE_2026-10-24.md` and `.tmp/vm-verification/r17-*`. Earlier failed/time-limited attempts remain documented as historical runs and are not presented as r17 failures or passes.
