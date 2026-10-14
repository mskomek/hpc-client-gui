# S4 Native GUI Diagnostic Runner

## Verdict

`S4_RUNNER_READY_SOURCE_LEVEL`

## Deliverable

Added `scripts/run_native_gui_gate.ps1`. It is a supervisor-only evidence wrapper; it makes no product changes, kills no processes, and does not change WER or LocalDumps settings.

Example invocation from the repository root:

```powershell
& .\scripts\run_native_gui_gate.ps1 `
  -ExecutablePath .\.venv\Scripts\python.exe `
  -ArgumentList @('-m', 'pytest', '-q', 'tests/test_w19_connection_lifecycle.py') `
  -EvidenceRoot .\.tmp\candidate5-final\native-runs `
  -WorkingDirectory (Get-Location).Path
```

Each invocation creates a GUID run directory under `EvidenceRoot`, gives the child a run-unique `WEBVIEW2_USER_DATA_FOLDER` and `TEMP`/`TMP`, captures stdout/stderr, and writes `run-evidence.json`. It periodically records the root process and observed descendants, including Python and WebView2 command lines. It also records any live process whose command line contains that unique profile path, so a WebView2 process that outlives its Python parent remains attributable to this run.

WER Application events 1000/1001 are queried only within the measured process interval. They are attributed only if an event's process ID matches a PID observed in the run's process tree/profile set, or its message contains the exact unique profile path. A time-window-only event is excluded. The manifest counts `0xC0000005`, `0xC000041D`, and `0xC0000409` among the attributed events. Event messages and full process command lines are retained as diagnostic evidence; review them for secrets before sharing outside the machine.

## Limitations and validation

- This runner observes process identity and ownership; it does not install or enable WER LocalDumps.
- A process that starts and exits entirely between 250 ms samples may be missed unless its WER event is separately tied to an observed run PID or exact profile path. Set `-PollMilliseconds 100` for short-lived child-heavy runs.
- WER records often omit profile paths. Those records require a PID match; matching the run time interval alone never qualifies.
- The runner does not clean up WebView2 processes or profile directories. Evidence and ownership remain available for supervisor review.
- No wx/WebView GUI tests were run by S4. PowerShell syntax validation and native behavior validation are left to the supervisor queue.

## Worktree identity

- Branch: `codex/c5-final-native-diagnostics`
- Base: `b0c6c65e2d9832937a5fd841573a0a99dc1f7a2f`
- Common thread-affinity repair is present in the worktree.
