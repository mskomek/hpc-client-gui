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
| Current develop sync regression | `python -m pytest -q tests/test_wx_logs_groups.py` at integration sync `1995d7f5cb28de5cdf34737f95202e9d4fb7af9b` | 10 passed, 0 failed | 0 |
| Current develop sync architecture gate | shared Agent Core + project gate, baseline `0aa8ce54321c9b5130bcf4366a88f8d731ac0898`, at integration sync `1995d7f5cb28de5cdf34737f95202e9d4fb7af9b` | PASS; 823 Python files, 50 LOC violations remain, 0 new import/API/cycle errors | 0 |
| Full release acceptance suite | `python scripts/release_test_suite.py --scope acceptance` | NOT RUN; retained for WAVE 12 full acceptance | — |
| GitHub Actions | not run | NOT RUN | — |

The first `py -m pytest` attempt used the global Python 3.14 installation, which has no pytest module; the WAVE 00 suite was rerun with the project `.venv` and passed 5/5. During Wave 01 source selection, one exploratory suite invocation had 44 passes and one failure because a later Jobs Wave 02 test rewrite patched an extracted module not yet present. That test-only rewrite was excluded from Wave 01; the final WAVE 01 suites passed 45/45 with the existing test retained and provenance assertions added. This diagnostic failure is source incompatibility, not an unresolved product failure.

## Pending suites

Focused suites will be added as waves land. Local and GitHub Actions results remain separate. Unrun suites must remain `NOT RUN`; skipped tests and environmental blockers are recorded individually and never counted as PASS.
