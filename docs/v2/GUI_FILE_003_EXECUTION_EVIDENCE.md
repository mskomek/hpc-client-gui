# GUI-FILE-003 Execution Evidence

## Environment

- Date: 2026-09-04
- OS: Windows-11-10.0.26200-SP0
- Python: 3.12.4 (`D:\Python\Python312\python.exe`)
- wxPython: 4.3.1 msw (phoenix), wxWidgets 3.3.3
- Branch: `develop`
- Tested commit: `db8d35926011529d3f0793c4d1e1920e791e42f4`

## Commands executed

```text
git status --short
git branch --show-current
git rev-parse HEAD
python --version
python -c "import sys; print(sys.executable)"
python -c "import wx; print(wx.version())"
git grep -n "GUI-FILE-003"
git grep -n "GUI-FILE-003 measured invariants"
python -m pytest -q tests/test_wx_file003_final_stress.py -s --cache-clear
python -m pytest -q tests/test_wx_*.py --cache-clear
$wxTests = Get-ChildItem -Path tests -Filter 'test_wx_*.py' | ForEach-Object { $_.FullName }; python -m pytest -q @wxTests --cache-clear
python -m pytest -q tests/test_wx_packaged_smoke.py --cache-clear
python scripts/wx_packaged_smoke.py
python -m pytest -q tests/test_transfer_concurrency.py tests/test_local_transfer_gate.py --cache-clear
python -m pytest -q tests/test_transfer_resume_semantics.py --cache-clear
python -m ruff check src tests
python scripts/qt_removal_gate.py
rg -n "def test_|STOR|APPE|REST|RETR|overwrite|resume|offset|read|write" tests/test_transfer_resume_semantics.py
git diff -- scripts/wx_packaged_smoke.py
git status --short
```

The literal wildcard command is not expanded by PowerShell and failed before collection; the immediately following expanded command executed the complete suite.

## Results

- Final stress: 11 passed, 0 failed, 0 skipped, 171.69s.
- Full wx suite: 330 passed, 0 failed, 0 skipped, 0 errors, 251.73s.
- Transfer concurrency/local gate: 14 passed, 0 failed, 0 skipped, 1.71s.
- Overwrite/resume semantics: 28 passed, 0 failed, 0 skipped, 0.45s.
- Ruff: all checks passed.

## Final stress counts

```text
right-click retarget: 200/200
local mutations: 100/100
remote mutations: 100/100
target switches: 200/200
navigate/completion races: 200/200
browser open/close: 50/50
blocked close-in-flight: 25/25
FILE transfer items: 100/100
unicode/space names: 50/50
reconnect session snapshots: 20/20
```

## Measured invariants

```text
wrong_targets: 0
stale_ui_overwrites: 0
destroyed_control_callbacks: 0
leaked_file_workers: 0
leaked_wx_windows: 0
duplicate_transfers: 0
lost_transfers: 0
leaked_transfer_sessions: 0
mixed_session_transfer_operations: 0
peak_local_mutation_concurrency: 1
peak_remote_mutation_concurrency: 1
lost_remote_mutations: 0
```

## Transfer semantic verification

`tests/test_transfer_resume_semantics.py` proved FTP and SFTP upload/download Overwrite versus explicit Resume at byte and protocol/offset level, including FTP `STOR`/`APPE`/`REST` behavior and SFTP truncate/seek behavior. The suite passed 28 tests.

## Qt removal gate

- Verdict: `NO-GO`
- Qt import points: 113
- Qt production files: 43
- Qt dependency records: 6
- Qt unique packages: 4
- Qt packaging references: 30
- Qt packaging files: 3
- Default GUI runtime: `qt`
- Additional blockers: 2 uncovered P0 parity rows; packaged/manual wx evidence is missing for Windows, Linux, and macOS.

## Scope limitation

The real-wx GUI-FILE-003 execution campaign was measured on Windows only.
