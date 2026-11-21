# V2 X11 / WebView acceptance: independent source-to-evidence review

Date: 2026-11-21
Repository: `mskomek/hpc-client-gui`
Original `develop`: `2be856dbc3d7a75f7149b1c6243e25af005de799`

## Inputs and limits

Reviewed the Google Drive acceptance campaign, including its main report, PR matrix,
Windows/Ubuntu native reports, X11 report, F-01 through F-06 findings and
manifest: https://drive.google.com/drive/folders/1P50aIbQUU-0av5-FoYnUrL7mIieSH5Re

Reviewed GitHub PR source at #67 `cbfdebee`, #76 `95de9ce7`,
#77 `42cb986c`, #78 `19c1e6ea`, #79 `ee34ef21` and `develop`.
The Drive manifest names 523 evidence entries, but raw test evidence was **not**
uploaded to Drive. Reported native exit codes and reproductions were not
independently executed in this GitHub-only review.

## Findings

### A. Contradictory WebView destruction contract — confirmed in source

- `tests/test_wx_terminal_webview_bridge.py::test_wx_terminal_close_releases_native_webview`
  expects `close()` to `Stop()` the view but **not** `Destroy()` the child.
- PR #77 added
  `tests/test_wx_terminal_native_teardown_contracts.py::test_explicit_close_preserves_standalone_child_destruction`,
  which expects **one** child `Destroy()` on explicit `close()`.
- `src/hpc_gui/wx_terminal_webview_lifecycle.py::close` on #77 calls
  `Destroy()` for an explicit close when `IsBeingDeleted()` is false and
  `_native_parent_teardown` is false.
- This native explicit-destroy behavior **also exists on the original
  `develop`**. The conflict is a pre-existing code/test inconsistency
  exposed by the new #77 contract tests; it cannot be attributed wholly to
  #77's code changes.
- F-02's isolated test failure and contradictory contract are independently
  supported by the source. The two competing tests cannot both pass unchanged.

Decision: parent wx ownership is the contract used for this follow-up:
`close()` detaches Python state and may stop a still-live initialized
controller, but does not directly destroy native children. `Destroy()`
and native parent events leave child destruction to wx. The tests for
both paths must agree.

### B. Parent-driven Stop during native teardown — native race risk

On #77, a ready WebView can be `Stop()`ped while its parent is already
tearing down. Backend callbacks may be in flight. The follow-up avoids
`Stop()` during parent teardown, deletion or pending native creation.

This is a safety change, **not** a proven root-cause fix for F-01.

### C. Native acceptance remains blocked

- F-01: Kole Ubuntu GNOME/Xwayland with WebView timed out on natural frame
  close in 3/3 trials; blank wx frame exited normally. No native stack trace
  or source-causality proof was retained.
- F-03: combined 4,016-test collection, first run exit 133 near 26%, second
  Xvfb run printed segmentation fault; no final JUnit. These do not prove
  identical root causes.
- F-04: Windows source GUI modules exceeded five minutes without final JUnit.
  The separate packaged 21/21 smoke does not close that gap.
- F-05: no suitable Windows X server; current Xwayland lacks SECURITY.
  #67 and #79 portable tests are green, but real trusted/untrusted SSH/X11
  remains BLOCKED_EXTERNAL. Do not enable `-ac` as a shortcut.
- F-06: release lock pins setuptools 84.0.0, affected by
  GHSA-xmj3-9gf7-h52w. First fixed version is 84.1.0. A separate Draft
  dependency PR contains the minimal pin change; no runtime exploit was shown.

## Change scope and residual acceptance

PR #80 addresses only the demonstrable ownership contradiction and
teardown race exposure, on top of PR #77. It **does not** claim F-01,
F-03, F-04 or F-05 is resolved.

Before V2 merge readiness:
1. Run standalone and combined lifecycle tests on the exact new source,
   including both earlier competing contract cases.
2. On Kole Ubuntu real GNOME/Xwayland, demonstrate natural WebView close
   with exit 0 in repeated processes; collect native debugger traces on
   remaining timeouts.
3. Complete Windows source GUI module run and obtain JUnit plus exit code.
4. Finish full combined pytest with exit 0 and complete 4,016-test or
   updated collection receipt; isolate signal 133 and the Xvfb segfault.
5. Provide an X SECURITY-capable Windows X server and verify real
   trusted/untrusted forwarding with authorized SSH and xclock.
6. Recheck release dependency lock/build packages and hash provenance
   after any changes.

No PR merge or release recommendation is made by this report.
