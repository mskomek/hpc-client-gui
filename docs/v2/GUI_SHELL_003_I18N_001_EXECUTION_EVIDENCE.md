# GUI-SHELL-003 / GUI-I18N-001 Execution Evidence

## Environment

- Date: 2026-09-04
- OS: Windows-11-10.0.26200-SP0
- Python: 3.12.4 (`D:\Python\Python312\python.exe`)
- wxPython: 4.3.1 msw (phoenix), wxWidgets 3.3.3
- Branch: `develop`
- Tested commit: `270d079398d2688159aeff6db0895ffd240cad7d`

## Commands executed

```text
git status --short
git branch --show-current
git rev-parse HEAD
python --version
python -c "import sys; print(sys.executable)"
python -c "import wx; print(wx.version())"
git grep -n "GUI-SHELL-003"
git grep -n "GUI-I18N-001"
python -m pytest -q tests/test_wx_shell.py --cache-clear
python -m pytest -q tests/test_wx_jobs.py tests/test_wx_jobs_behavior.py --cache-clear
python -m pytest -q tests/test_wx_*.py --cache-clear
$wxTests = Get-ChildItem -Path tests -Filter 'test_wx_*.py' | ForEach-Object { $_.FullName }; python -m pytest -q @wxTests --cache-clear
python -m pytest -q tests/test_wx_shell_i18n.py --cache-clear
python -m pytest -q tests/test_wx_shell_p0.py tests/test_wx_shell_p0_stress.py -s --cache-clear
python -m pytest -q tests/test_wx_file_context_i18n.py --cache-clear
python -m pytest -q tests/test_wx_packaged_smoke.py --cache-clear
python scripts/wx_packaged_smoke.py
python -m compileall -q src tests
python -m ruff check src tests
git diff --check
python scripts/qt_removal_gate.py
```

The literal wildcard command failed before collection because PowerShell does not expand that argument. The expanded command executed the full wx suite.

## GUI-SHELL-003

PROVEN. Real wx shell/job event chains prove disappeared-job final-state lookup, translated completion/failure notifications, `COMPLETING` suppression, initial-poll suppression, duplicate prevention, reconnect generation isolation, tray-unavailable tracking, real close handling, idempotent cleanup, blocked-poll close, and active-transfer close.

```text
job terminal transitions: 100/100
duplicate-poll checks: 100/100
session/reconnect stale completions: 50/50
shell normal open/close: 50/50
blocked job-poll close: 25/25
active-transfer close: 25/25
repeated shutdown calls: 50/50
```

## GUI-I18N-001

PROVEN. Real wx menu events select English/Türkçe, update radio check state, attach packaged flag bitmaps, and retranslate the shell and an already-open Jobs window without restart. Existing local/remote/transfer runtime i18n tests also passed.

```text
language switches EN/TR/EN: 100/100
```

## Measured invariants

```text
duplicate_job_notifications: 0
missed_final_notifications: 0
stale_session_notifications: 0
post_close_tray_notifications: 0
duplicate_cleanups: 0
destroyed_control_callbacks: 0
leaked_shell_windows: 0
leaked_transfer_sessions: 0
wrong_language_labels: 0
missing_translation_labels: 0
post_close_language_callbacks: 0
```

## Results

- Focused shell tests: 4 passed.
- Focused jobs tests: 10 passed.
- Focused i18n tests: 2 passed.
- P0 shell/stress tests: 14 passed in 76.37s, no skips or errors.
- Existing wx local/remote/transfer i18n tests: 5 passed.
- Packaged wx smoke: 1 passed; all six stages passed.
- Compileall, Ruff, and diff check passed.

The full wx suite executed 346 tests: 345 passed, 1 failed, 0 skipped, 0 errors, 313.45s. The single failure is the pre-existing Windows clipboard test `test_wx_remote_copy_path_preserves_multiple_selected_paths`; it passes in isolation and does not involve either P0 row.

## Tray and platform scope

The tray adapter path is proven with a deterministic injected adapter. Tray-unavailable behavior is proven without requiring a physical OS tray. Physical notification display availability remains platform-dependent.

The real-wx GUI-SHELL-003 and GUI-I18N-001 execution campaign was measured on Windows only.

## Parity and Qt gate

```text
GUI-SHELL-003: COVERED
GUI-I18N-001: COVERED
Qt removal verdict: NO-GO
Qt import points: 113
Qt production files: 43
Qt dependency records: 6
Qt unique packages: 4
Qt packaging references: 30
Qt packaging files: 3
Default GUI runtime: qt
Remaining uncovered P0 rows: 0
```

Qt/PySide6/shiboken6 were retained. `GUI-TERM-002` and `GUI-EDIT-002` remain outside this wave and are still `PARTIAL`.
