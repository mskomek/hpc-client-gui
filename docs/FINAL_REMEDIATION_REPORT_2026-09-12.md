# Final remediation report — 2026-09-12

## Repository state

- Branch: `develop`
- Starting and final HEAD: `12ce79935bf076e1062c57dc7dbd148bad2bfae1`
- The worktree was already dirty and remains dirty. The checks below describe
  the local working tree based on that HEAD, not a clean checkout.
- Existing local changes and untracked files were preserved. `.tmp/` was not
  touched. No commit or push had been made when this snapshot was recorded.

## CI

**Automatic GitHub Actions CI: DISABLED.** The former automatic CI workflow is
archived at `docs/ci-disabled/ci.yml`, outside `.github/workflows/`. The only
workflow currently in `.github/workflows/` is `release.yml`, which is manual
(`workflow_dispatch`) only. Disabling CI is not a CI-pass result.

## Verification results

| Command/check | Result | Details |
|---|---|---|
| `python -m compileall -q src/hpc_gui` | PASS | Completed successfully. |
| `python -m ruff check src scripts tests` | PASS | `All checks passed!` |
| `python scripts/check_i18n.py` | PASS | All three checks passed. |
| `python scripts/smoke_test.py` | PASS | Completed successfully. |
| `python -m pytest tests/test_plugin_contract.py -q --tb=short -rf` | PASS | 10 passed against the official plugin checkout pinned at `4e79325873a3eda232071339b367722ccacbb8f8`. The test used `HPC_GUI_CONTRACT_REPO` pointing at that checkout. |
| `python -m pytest tests/test_plugin_v2_integration.py -q --tb=short -rs` | PASS | 4 passed against the same pinned plugin checkout. |
| `python -m pytest tests/test_plugin_security.py -q --tb=short -rf` | PASS | 22 passed; 0 skipped. Arbitrary modified commands remain rejected. |
| `python -m pytest tests/test_app_updater.py tests/test_updater_helper.py tests/test_wx_updater_spec.py tests/test_wx_migration.py tests/test_transfer_parallelism_migration.py -q --tb=short -rf` | PASS | 63 passed; 0 skipped. This includes focused updater and migration coverage. |
| CLI/SSH/SFTP/packaging focused pytest set | PASS | 222 passed and 9 subtests passed. The original aggregated record did not retain the full invocation. |
| `python -m pytest tests/test_wx_terminal.py tests/test_wx_terminal_webview.py tests/test_wx_terminal_parity_evidence.py tests/test_wx_embedded_terminal.py tests/test_wx_terminal_behavioral.py -q --tb=short -rf` | PASS (unit tests) | 70 passed in 74.74 seconds. This does not establish packaged WebView2 parity. |
| `python -m pytest tests/test_performance_probe.py::PerformanceProbeTests::test_qt_event_loop_block_is_detected -q --tb=short -rf` | PASS | Three isolated successful runs after the test was made to wait for its first monitor heartbeat before deliberately blocking the GUI thread. |
| `python scripts/release_test_suite.py` | PASS | Base suite: 1,896 passed, 21 skipped, 2 deselected; all isolated groups passed. `wx_jobs_behavior` separately had 3 Windows-flaky skips. |
| `python scripts/release_test_suite.py --coverage` | PASS | All groups passed; measured coverage 66.05%, against a 65% minimum. `coverage.json` and `coverage.xml` were generated, then removed during cleanup. |
| `python scripts/wx_packaged_smoke.py --artifact dist/hpc-client-gui/hpc-client-gui.exe --platform windows` | FAIL | Current-attempt artifact SHA-256 `c83c1b05c157a97b040c705efe722855cd1511ee3b59de19c87341e18a38394f`, built from a dirty worktree based on this HEAD. Foreground activation was denied; the guarded test sent no keys and DOM/bridge/SSH input counts were zero. This was not a clean-HEAD release artifact. |
| Earlier Windows packaged smoke using artifact SHA-256 `21141a8b3bb272269234bb18136afefe49927fa5530f85ca8aa5cec64c6c8394` | FAIL | Foreground matched and 36/36 `SendInput` events were accepted, but no terminal output was produced. |
| Ubuntu 24.04 Docker Qt-only packaged smoke | PASS (limited) | Python 3.12.3 offscreen GUI stayed up for 20 seconds. This used the Linux PyInstaller spec and `scripts/linux_release_smoke.py --gui`, with wxPython omitted; it is not Linux wx/WebKit evidence. |
| Ubuntu full `requirements-release.lock` install | FAIL / environment blocked | Pinned `wxPython==4.3.1` required a source build; the cached image had no `gcc`/C compiler. The complete locked Linux release environment was not reproduced. |
| `scripts/capture_current_gui_wx.py` | PASS (limited) | Current source wx UI screenshots were captured using mock data in `%TEMP%`; these are not packaged evidence or human sign-off. |

Release-suite skip accounting: 14 plugin tests were run separately against
the pinned plugin checkout; 4 symlink/POSIX-only checks, one POSIX permission
check, and one POSIX case-sensitivity check were unavailable on Windows; one
historical screenshot manifest refers to an older SHA. Two packaging-marked
tests were deselected. Skips and deselections are not counted as passes.

## Changes and findings

- The wx-only GUI test module skips at collection when wxPython is unavailable,
  so Qt-only environments do not require wxPython merely to collect tests.
- Updater exception callbacks keep durable error strings rather than capturing
  Python exception variables after the `except` scope. Undefined wx/time and
  stale imports were addressed. The fake install-copy progress path was
  removed in favor of the actual update artifact path.
- The compatibility validator accepts the exact published legacy TRUBA
  `sacct_command` variant while continuing to reject arbitrary command strings.
  The plugin repository was used for verification but was not modified.
- `GUI-TERM-001` evidence now distinguishes historical packaged success from
  current reproducible evidence. The current packaged attempt failed; the
  separate `0x80004004 Operation aborted` was reproduced when WebView2 creation
  was cancelled by destroying its host before asynchronous creation completed.
  The exact internal WebView2 COM method was not captured. This teardown
  cancellation is distinct from the latest packaged attempt's
  `keyboard_input:foreground_lost` failure.
- Migration tests cover the available legacy profile/config paths, including
  idempotence, rollback safety, unknown-key preservation and exclusion of
  secrets from diagnostics. Complete historical fixtures for keychain,
  provider, quota, updater and terminal-history state were not available.
- Terminal Unicode input/output has focused test coverage in the passing wx
  terminal set. This does not substitute for current packaged keyboard-to-PTY
  evidence or a complete category-by-category historical migration audit.
- Generated coverage files, pytest/cache directories and the generated
  `dist/hpc-client-gui` artifact were removed after validation. The tested
  packaged report remains recorded at
  `build/audit/wx-packaged-smoke-windows.json`.

## Final TODO/status audit

| Area | Status | Evidence | Remaining risk |
|---|---|---|---|
| Automatic CI disabled | PASS | No automatic workflow remains in `.github/workflows/`; archived workflow is outside it. | CI will not provide automated push/PR validation. |
| Local lint, compile and basic checks | PASS | Compileall, Ruff, i18n and smoke commands above. | Results are from the dirty local tree. |
| Official plugin contract/security | PASS | Contract 10 passed; V2 integration 4 passed; security 22 passed against the pinned official plugin revision. | Plugin repository itself was not modified. |
| Updater focused behavior | PASS | Focused updater/migration command: 63 passed. | Current packaged installer execution and cross-platform install/update are not evidenced. |
| Qt-only/wx test isolation | PASS | wx-dependent test collection uses `pytest.importorskip("wx")` before wx-dependent imports; release suite completed locally. | wx-native behavior still depends on platform/runtime evidence. |
| Terminal unit/adapter tests | PASS | Focused terminal command: 70 passed, including Unicode, lifecycle and adapter tests. | Unit/fixture evidence is not full visible packaged parity. |
| `GUI-TERM-001` terminal parity | PARTIAL | Current packaged keyboard→xterm→PTY output was not demonstrated; current test evidence is recorded in `docs/v2/GUI_TERM_001_EXECUTION_EVIDENCE.json`. | Windows WebView2 packaged input/output, alternate-screen rendering and live backend remain unverified. |
| Current packaged Windows smoke | FAIL | Current dirty-worktree artifact failed guarded foreground input; previous foreground-matched artifact also had no terminal output. | Rebuild and reproduce from a clean current artifact, then fix the actual input/output boundary. |
| Linux/macOS packaged GUI evidence | NOT EVIDENCED | Linux Qt-only offscreen smoke is limited evidence; full Linux wxPython lock install was blocked. No current macOS packaged runtime was produced. | Linux wx/WebKit and macOS package/runtime remain unverified. |
| Existing-user migration | PARTIAL | Available legacy config/profile migration and safety properties have tests. | Authentic historical keychain/provider/quota/updater/terminal-history fixtures are missing. |
| Live cluster and production transport | NOT EVIDENCED | No live TRUBA/HPC scheduler operation or production SSH/SFTP was performed. | Requires authorized live environment and release verification. |
| Current screenshot/manual GUI sign-off | NOT EVIDENCED | Source/mock screenshots exist only as limited implementation evidence. | No current packaged screenshot review or human sign-off. |
| Worktree cleanliness | FAIL | `git status` showed existing staged/unstaged edits and untracked local files; they were preserved. | Review and stage changes intentionally before committing. |

## Final verdicts

- Repository-side remediation: **REPOSITORY NOT CLEAN** — local verification is
  strong, but the worktree is dirty and the current Windows packaged smoke
  failed.
- Terminal parity: **PARTIAL**.
- Existing-user migration: **PARTIAL**.
- Current packaged Windows evidence: **FAIL**.
- Full release suite: **PASS** (including the separate coverage run).
- Overall release: **RELEASE NO-GO**.

The plugin repository was not changed. No current live-cluster, cross-platform
packaged-runtime, current Windows packaged terminal-parity, or manual GUI
sign-off evidence is claimed. No CI-pass claim is made.

## Follow-up verification during test-governance preparation

This report preserves the earlier remediation run results above. Later focused
revalidation on the same Windows host found two unresolved lifecycle defects;
the earlier passing results are not evidence that these later reproductions
pass:

- `tests/test_wx_shell_p0_stress.py::test_wx_shell_p0_stress_real_wx_paths`
  observed a remote-files completion callback call `notebook.GetSelection()`
  after its wx Notebook had been destroyed. Python raised
  `RuntimeError: wrapped C/C++ object of type Notebook has been deleted` at
  `src/hpc_gui/wx_remote_files_view.py:592` via `_commit_navigation` and
  `_update_navigation_buttons`.
- `tests/test_wx_terminal_behavioral.py::test_find_next_prev_advances_through_matches`
  produced a Windows native access violation while closing a WebView2 panel at
  `src/hpc_gui/wx_terminal_webview.py:979`.

The affected validation packet was stopped without production-code changes.
Current status is **DEFECT_FOUND**; `GUI-TERM-001` remains **PARTIAL** and the
current packaged Windows smoke remains **FAIL**.
