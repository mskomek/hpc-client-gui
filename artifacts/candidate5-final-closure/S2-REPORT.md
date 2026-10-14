# S2 — WebView2 test process hygiene

Verdict: `S2_HYGIENE_FIX_READY`

## Findings

- `tests/test_wx_terminal_webview.py` starts native child interpreters in five inline `subprocess.run` sites and in `_run_subprocess_test`.
- Before this change, each path copied the parent environment and set only `PYTHONPATH`. It did not set `WEBVIEW2_USER_DATA_FOLDER`, `TEMP`, or `TMP`. Therefore all children inherited the same parent WebView profile setting when one was configured, or used the same WebView2 default for the same Python executable.
- `D:\Projeler\.tmp\hpc-client-gui\candidate5-native-ablation\B\B-REPORT.md` records a serial terminal run using one unique suite-level WebView data directory that left 13 WebView2 processes whose command lines referenced that directory. This directly confirms that child WebView processes can outlive their Python child and overlap later subprocesses on a shared profile.
- The same report records one terminal node failure (`not ready`) with `E_ABORT` in that run. The earlier parallel WER events were explicitly unattributed, so they are not evidence of a B-owned native crash.
- `release_test_suite.py` runs `tests/test_wx_terminal_webview.py` in its own pytest process, but does not manage per-child WebView profiles. File-level isolation therefore does not prevent profile reuse among the terminal test's subprocess children.

## Change prepared

`tests/test_wx_terminal_webview.py` routes all five inline native subprocess launches through `_run_subprocess_test`. That helper assigns a fresh `WEBVIEW2_USER_DATA_FOLDER` for every child under a configurable test temp root (`HPC_CLIENT_GUI_TEST_TEMP_ROOT`), defaulting to the repository `.tmp` directory. It intentionally does not kill WebView processes or remove profile directories: those actions require ownership/liveness evidence because WebView2 can outlive the Python process.

No change was made to `src/hpc_gui/wx_terminal_webview.py`. No native GUI/WebView test was run by S2.

## Supervisor commands

Run these serially through the native GUI queue. The test helper gives every native child a unique profile; each pytest run also gets its own basetemp. Preserve logs and process/WER snapshots in the supervisor's run directory.

```powershell
Set-Location D:\Projeler\.worktrees\hpc-c5-final-s2
$env:HPC_CLIENT_GUI_TEST_TEMP_ROOT = 'D:\Projeler\.tmp\hpc-client-gui\s2-webview-test'
python -m pytest -q --basetemp D:\Projeler\.tmp\hpc-client-gui\s2-webview-test\pytest-01 tests/test_wx_terminal_webview.py
python -m pytest -q --basetemp D:\Projeler\.tmp\hpc-client-gui\s2-webview-test\pytest-02 tests/test_wx_terminal_webview.py
python -m pytest -q --basetemp D:\Projeler\.tmp\hpc-client-gui\s2-webview-test\pytest-03 tests/test_wx_terminal_webview.py
```

For reference comparison, run the same command once from the common-repair reference checkout before these three modified-suite runs, with a distinct `HPC_CLIENT_GUI_TEST_TEMP_ROOT` and basetemp. Keep all four runs serialized. Accept the S2 fix into final integration only if the modified suite is `29/29 PASS` in all three runs with zero `E_ABORT`, readiness failures, native AV signatures, and run-owned WER crashes.

## Validation status

- Static source review completed.
- Native validation pending supervisor execution; no GUI tests were run in this worktree.
- No product runtime change, process termination, commit, or push was made.
