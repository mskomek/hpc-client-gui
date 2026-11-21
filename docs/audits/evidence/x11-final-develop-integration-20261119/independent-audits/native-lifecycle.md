# Independent native lifecycle audit (transcribed)

- Auditor: read-only subagent `audit_native_lifecycle`.
- Severity: **HIGH — OPEN** for native GUI stability; Windows root cause remains unverified.

## Linux evidence reviewed

1. Full Python 3.14.8 XRDP pytest run `py314-full-pytest-display-20261120T050309Z` exited 139 at 74%, no JUnit. The crash occurred at `tests/test_wave80_files_outputs_audit_behavior.py:225` in `wx.Yield()`, with an unsymbolized `libjavascriptcoregtk` C-stack frame. A→C mini-sequence passed the first Jobs UI test, then crashed in the second; C alone passed 1/1. GDB later showed `wxEvtHandler::SafelyProcessEvent` → `wxTimerImpl::SendEvent` → `sipwxTimer::Notify` → GTK timeout callback → wx yield. This supports timer/event dispatch as a hypothesis but does not identify the timer owner/target.
2. Exact Git-checkout full suite `py314-final-gitdepth100-full-20261120T123000Z` exited 139 near 48%, no JUnit. The Python frame was `wx_terminal_webview.py:350` (`SetMinSize` in that exact checkout) during `tests/test_w04_menu_actions.py::test_plugin_action__success__silent`; five prior failures were missing ignored historical screenshot fixtures.
3. That W04 node alone also exited 139 in an uninstrumented run at `tests/w04_support_freeze_support.py:62` (`wx.Yield`) with JavaScriptCore on the C stack. A GDB-instrumented run of the same test passed 1/1 and the inferior exited normally, so timing/debugger changes alter the outcome.

These are two Linux wxGTK failure paths with different Python frames; they are not proof of one shared cause. Neither establishes the historical Windows wxMSW/WebView2 crash cause.

## Windows evidence reviewed

The Windows11-New Session 1 bridge module passed 9/9. Ten current First250+navigation runs passed, but the navigation test runs in a child process. R14's historical failing target was same-process and exited `0xC0000005`; therefore those isolated passes do not close the historical path. Last1000/same-process follow-up and WER cleanup remain blocked while Kole is unreachable.

## Recommended next proof

Identify the timer/event target and ownership at the GDB fault, compare with C-alone, and instrument/repair its actual cleanup only after owner evidence. On Windows, restore a reachable real Session 1 and rerun historical same-process predecessor stress plus the Last1000 order with native process exit and dump/JUnit evidence. Do not infer `NATIVE_CRASH_FIXED` from the Linux or isolated Windows passes.
## 2026-11-20 follow-up

**Severity: HIGH — OPEN; root cause UNVERIFIED.** Independent read-only follow-up reviewed the exact-runtime full-run, isolated plugin teardown run, and GDB repeat. It observed distinct Linux wxGTK crash paths: full-suite crash at `wx.Yield()` in the Jobs follow-menu test (native stack includes `libjavascriptcoregtk` but does not identify a timer target); isolated plugin crash at `_close_shell`'s first `wx.Yield()` (GDB repeat passed); and an earlier WebView construction/use crash at `SetMinSize`. These do not prove one shared cause or that JavaScriptCore is defective. Historical Windows WebView2 remains a separate unresolved path. Recommended discrimination: repeat each target alone, then add captured immediately preceding tests in the same process, collecting complete native stack/registers and event target at crash.

## 2026-11-20 Windows v6 shutdown follow-up

**Severity: HIGH — OPEN.** A read-only subagent reviewed the Session 1 v6 GUI close receipt and CDB thread stacks. The main thread remains in `wxAppConsoleBase::MainLoop` waiting for messages after the main HWND disappeared, so the immediate state is event-loop retention rather than a synchronous close callback blocked inside WebView2 teardown. The dump does not show the remaining wx top-level windows, `GetExitOnFrameDelete()` value, top-window identity, or whether wx processed the frame's `EVT_WINDOW_DESTROY`; the underlying exit condition remains unverified.

Recommended discriminator: capture those wx app/window values before and after frame destruction and after `EVT_WINDOW_DESTROY`. If no top-level windows remain and exit-on-frame-delete is enabled but the loop stays active, test a guarded `ExitMainLoop()` only after confirming all top-level windows are gone. Do not add an unconditional event-loop exit. See `../windows/v6-close-investigation-20261120/` for the package-bound receipt and native stack log.
