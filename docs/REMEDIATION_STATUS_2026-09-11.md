# Remediation status — 2026-09-11

This record describes only validation run locally on Windows 11, Python 3.12.4,
from `develop` at starting HEAD `cac3c38f31c4bf453c7b922b7898b9637855c9d8`.
Pre-existing working-tree changes were preserved.

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
| `python -m pytest tests/test_plugin_contract.py -q --tb=short -rf` | PASS — 10 passed against the pinned plugin checkout `4e79325873a3eda232071339b367722ccacbb8f8` |
| `python -m pytest tests/test_plugin_security.py -q --tb=short -rf` | PASS — 22 passed |
| `python -m pytest tests/test_wx_updater_spec.py tests/test_app_updater.py tests/test_update_verification.py tests/test_linux_update_handoff.py -q --tb=short -rs` | PASS — 42 passed, 1 skipped because symlink creation is unavailable on Windows |
| `python -m pytest tests/test_wx_migration.py tests/test_shortcut_preferences.py tests/test_paths.py -q --tb=short -rs` | PASS — 12 passed, 1 skipped because symlinks are unavailable on Windows |
| CLI/SSH/SFTP/packaging focused pytest set | PASS — 222 passed, 9 subtests passed |
| `python -m pytest tests/test_wx_terminal.py tests/test_wx_terminal_webview.py tests/test_wx_terminal_parity_evidence.py tests/test_wx_embedded_terminal.py tests/test_wx_terminal_behavioral.py -q --tb=short -rf` | FAIL — 60 passed, 8 failed, 2 xpassed; WebView2 reported `Operation aborted` on this host, and the stale source assertion was corrected separately |
| `python -m pytest tests/test_wx_packaged_smoke.py -q --tb=short -rf` | FAIL — required packaged artifact is absent (`build/audit/wx-artifact-windows.missing`) |
| `python scripts/release_test_suite.py` | INTERRUPTED — compile, i18n, and smoke gates passed; the full pytest gate was still active after several minutes and was stopped rather than reported as a result |
| `python scripts/release_test_suite.py --coverage` | NOT RUN — base release suite did not complete |

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
- Migration remains **PARTIAL**: current tests prove legacy profile/config
  migration, idempotence, rollback safety, unknown-key preservation, and secret
  exclusion from diagnostics. Full historical settings, keychain, provider,
  updater, and terminal-history migrations were not reproduced from complete
  historical fixtures.
- `GUI-TERM-001` remains **PARTIAL**. Local source/behavior tests cover the
  WebView/xterm bridge where the host supports it, but this run did not reproduce
  packaged WebView2 readiness, alternate-screen rendered-state evidence, or
  live-cluster terminal behavior.

## Not evidenced here

No live TRUBA/HPC operation, scheduler submission, production SSH/SFTP,
packaged Linux/macOS runtime, current packaged Windows WebView2 success,
cross-platform installer/update execution, or current-build screenshot was
claimed.
