# Remediation status — 2026-09-12

This record describes validation run locally on Windows 11, Python 3.12.4,
from `develop` at starting HEAD `12ce79935bf076e1062c57dc7dbd148bad2bfae1`.
Pre-existing working-tree changes were preserved. The worktree was dirty;
therefore local checks describe that working tree, not a clean checkout of HEAD.

## CI

GitHub Actions CI is intentionally disabled. The former automatic workflow is
preserved at `docs/ci-disabled/ci.yml`, outside `.github/workflows/`; normal
pushes and pull requests therefore create no CI runs. `release.yml` remains a
manual-only workflow. This is not a CI-pass claim.

## Local commands

| Command | Result |
|---|---|
| `python -m compileall -q src/hpc_gui` | PASS |
| `python -m ruff check src scripts tests` | PASS — `All checks passed!` |
| `python scripts/check_i18n.py` | PASS — all three checks OK |
| `python scripts/smoke_test.py` | PASS |
| `HPC_GUI_CONTRACT_REPO=<temporary checkout at 4e79325873a3eda232071339b367722ccacbb8f8> python -m pytest tests/test_plugin_contract.py -q --tb=short -rf` | PASS — 10 passed against a fresh official plugin checkout at the pinned commit |
| `HPC_GUI_CONTRACT_REPO=<same pinned checkout> python -m pytest tests/test_plugin_v2_integration.py -q --tb=short -rs` | PASS — 4 passed |
| `python -m pytest tests/test_plugin_security.py -q --tb=short -rf` | PASS — 22 passed, 0 skipped |
| `python -m pytest tests/test_app_updater.py tests/test_updater_helper.py tests/test_wx_updater_spec.py tests/test_wx_migration.py tests/test_transfer_parallelism_migration.py -q --tb=short -rf` | PASS — 63 passed, 0 skipped |
| CLI/SSH/SFTP/packaging focused pytest set | PASS — 222 passed, 9 subtests passed |
| `python -m pytest tests/test_wx_terminal.py tests/test_wx_terminal_webview.py tests/test_wx_terminal_parity_evidence.py tests/test_wx_embedded_terminal.py tests/test_wx_terminal_behavioral.py -q --tb=short -rf` | PASS — 70 passed; a separate native WebView2 host attempt still reports `0x80004004 Operation aborted`, so parity remains PARTIAL |
| `python -m pytest tests/test_performance_probe.py::PerformanceProbeTests::test_qt_event_loop_block_is_detected -q --tb=short -rf` | PASS — three isolated runs after making the test block only after the first monitor heartbeat. The first full release-suite attempt exposed a timing race in this test; the rerun passed. |
| Earlier `python -m pytest tests/test_wx_packaged_smoke.py -q --tb=short -rf` | HISTORICAL PASS only — artifact SHA-256 `31efff023feeb684c61c6916398f27a2c1b8e73a75cbfbcd7c7af6c66badb47e`; not the current artifact |
| `python scripts/wx_packaged_smoke.py --artifact dist/hpc-client-gui/hpc-client-gui.exe --platform windows` | FAIL — latest artifact SHA-256 `c83c1b05c157a97b040c705efe722855cd1511ee3b59de19c87341e18a38394f`, dirty worktree based on HEAD `12ce79935bf076e1062c57dc7dbd148bad2bfae1`; foreground activation was denied, so guarded input sent no keys and DOM/bridge/SSH input counters were zero. A preceding artifact `21141a8b…` accepted 36/36 foreground `SendInput` events but produced no terminal output. Neither is a clean-HEAD release artifact. |
| Ubuntu 24.04 Docker: PyInstaller Linux spec + `scripts/linux_release_smoke.py --gui` | PASS — Qt-only artifact, Python 3.12.3, offscreen GUI remained up for 20 seconds; the pinned lock was used with only `wxPython` omitted |
| Ubuntu full `requirements-release.lock` install | FAIL — pinned `wxPython==4.3.1` fell back to source build; cached image lacks `gcc`/C compiler, so this was not the full official Linux release build |
| `scripts/capture_current_gui_wx.py` | PASS — current source wx shell screenshots captured with disposable mock profile/session in `%TEMP%`; not packaged evidence or manual sign-off |
| `python scripts/release_test_suite.py` | PASS — base suite 1896 passed, 21 skipped, 2 deselected; all isolated groups passed. Skips: 14 plugin tests ran separately with the pinned checkout; 4 symlink/POSIX-only checks unavailable on Windows; 1 historical screenshot manifest targets an older SHA; 1 POSIX permission check; 1 POSIX case-sensitivity check. Two packaging-marked tests were deselected. `wx_jobs_behavior` additionally had 3 pre-existing Windows-flaky skips. |
| `python scripts/release_test_suite.py --coverage` | PASS — all groups passed; final coverage 66.05% (65% required); `coverage.json` and `coverage.xml` were generated for the run and removed during artifact cleanup |

## Remediation notes

- wx-only collection now uses `pytest.importorskip("wx")` before wx-dependent
  imports in `tests/test_gui_verification.py`; Qt-only environments do not
  need wxPython installed for collection.
- Updater callbacks retain durable error strings instead of referencing cleared
  exception variables. Undefined wx/time/import issues were removed, and the
  fake install-copy progress path was removed in favor of the verified update
  artifact path.
- The plugin validator accepts the exact published legacy TRUBA `sacct_command`
  format as a compatibility variant. Arbitrary command strings remain rejected.
  Only this application repository was modified; the plugin checkout was used
  for contract verification and was not changed.
- The event-loop probe test now schedules its deliberate GUI-thread block after
  the first timer heartbeat. This keeps the integration assertion deterministic
  without weakening its 80 ms delay requirement.
- Migration remains **PARTIAL**: current tests prove legacy profile/config
  migration, idempotence, rollback safety, unknown-key preservation, and secret
  exclusion from diagnostics. Full historical settings, keychain, provider,
  updater, and terminal-history migrations were not reproduced from complete
  historical fixtures.
- `GUI-TERM-001` remains **PARTIAL**. The current Windows package reached the
  WebView-ready smoke phase and its loopback PTY resize check passed. The latest
  guarded attempt could not foreground the package and sent no keys; a preceding
  foreground-matched attempt sent 36/36 native input events but produced no
  terminal output. The packaged gate result is FAIL, not parity evidence.
  A separate native `0x80004004` was reproduced when WebView2 creation was
  intentionally cancelled by destroying the host before async creation ended;
  the exact internal WebView2 COM method was not captured. This teardown case
  is distinct from the latest packaged smoke's `keyboard_input:foreground_lost`.
  Alternate-screen packaged rendering and live-cluster behavior remain open.
- Packaged smoke report identity is SHA-256 `c83c1b05…`; the preceding
  foreground-matched input attempt used `21141a8b…`. Detailed results are in
  `docs/v2/WX_PACKAGED_SMOKE_GATE.md`.
- Linux current Qt offscreen package startup was reproduced, but the complete
  locked Linux release environment was not: its wxPython source build is missing
  a compiler. This does not establish Linux wx/WebKit support.
- The screenshot script now selects wx pages by their actual page handles. It
  captured current source UI using mock data; context-menu capture is omitted
  because synthetic native menu activation blocks the capture loop. The images
  are not packaged evidence and have no human sign-off.

## Not evidenced here

No live TRUBA/HPC operation, scheduler submission, production SSH/SFTP,
macOS packaged runtime, Linux wx/WebKit packaged runtime, terminal keyboard-to-
PTY/output parity in the current Windows package, alternate-screen packaged
rendering, cross-platform installer/update execution, or manual GUI sign-off was
claimed. Current source wx screenshots and Linux Qt offscreen startup are
limited evidence; neither is a full release/platform sign-off.

## Follow-up during test-governance preparation — 2026-09-12

The earlier passing terminal and release-suite results above are a snapshot of
the remediation run recorded at that time. Subsequent focused revalidation
found two wx lifecycle defects; no production code was changed in response.

- `tests/test_wx_shell_p0_stress.py::test_wx_shell_p0_stress_real_wx_paths`
  emitted `RuntimeError: wrapped C/C++ object of type Notebook has been
  deleted` from the remote-files completion callback at
  `src/hpc_gui/wx_remote_files_view.py:592`, through `_commit_navigation` and
  `_update_navigation_buttons`, ending at `notebook.GetSelection()`. The
  callback ran after the owning view had been destroyed. The focused stress
  execution was stopped after capturing this evidence.
- `tests/test_wx_terminal_behavioral.py::test_find_next_prev_advances_through_matches`
  triggered a Windows native access violation while
  `WxTerminalWebViewPanel.close()` destroyed WebView2 at
  `src/hpc_gui/wx_terminal_webview.py:979`. This remains an unresolved runtime
  lifecycle defect.
- The terminal WebView module passed alone (29 tests), parity evidence passed
  alone (11), embedded-terminal tests passed alone (9), and the terminal header
  status node passed alone (1). The combined terminal run had a 15-second
  subprocess timeout on that header node; this is recorded separately from the
  native access violation.

Current overall test-governance execution status is **DEFECT_FOUND**. The two
lifecycle findings remain open; the preceding packaged Windows smoke remains
**FAIL** and `GUI-TERM-001` remains **PARTIAL**.
