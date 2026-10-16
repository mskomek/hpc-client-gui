"""Finalize child-side wx smoke evidence after teardown readback."""
from __future__ import annotations

import json
from pathlib import Path


def _frame_destroyed(wx, frame) -> bool:
    """Fail-closed proof that wx removed and deleted the native frame.

    wxPython has no wx.IsDestroyed. Python membership on wx frames invokes
    C++ equality on a deleted wrapper, turning successful cleanup into FAIL.
    """
    try:
        # Identity comparison never dispatches into a deleted C++ wrapper.
        if any(window is frame for window in wx.GetTopLevelWindows()):
            return False
        probe = getattr(frame, "IsBeingDeleted", None)
        if not callable(probe):
            # Lightweight test doubles have only the authoritative registry.
            return True
        probe()
    except RuntimeError as exc:
        # Native wrapper deletion is stronger than a scheduled Destroy().
        # Unrelated GUI/runtime exceptions must NOT count as destruction.
        description = str(exc)
        return (
            "wrapped C/C++ object" in description
            and "has been deleted" in description
        )
    except Exception:
        return False
    # An accessible C++ object is not yet deleted, regardless of Hide/Destroy
    # requests or a momentary absence from the top-level registry.
    return False


def finish_packaged_smoke(state, checks, error, output_path, app, wx, frame, session_state, lifecycle):
    if state["done"]:
        return
    state["done"] = True
    if checks.get("clean_shutdown") != "FAIL":
        checks["clean_shutdown"] = "PENDING"
    panel = session_state.get("_embedded_terminal_panel")
    if panel is not None and getattr(panel, "_ready", False):
        diagnostic = state.setdefault("input_diagnostic", {})
        diagnostic["bridge_input_chars"] = state["bridge_input_chars"]
        diagnostic["ssh_input_chars"] = state["ssh_input_chars"]
        raw_events = panel._run_js_readback(
            "JSON.stringify(window.__hpcSmokeInputEvents || null)"
        )
        if raw_events:
            try:
                diagnostic["dom_input_events"] = json.loads(raw_events)
            except json.JSONDecodeError:
                diagnostic["dom_input_events"] = "invalid JSON"
    payload = {
        "schema": "wx-packaged-runtime/1",
        "result": state["result"],
        "checks": checks,
        "phase": state.get("phase"),
        "input_diagnostic": state.get("input_diagnostic"),
        "last_line": state.get("last_line"),
        "last_buffer": state.get("last_buffer"),
        "last_screen": state.get("last_screen"),
        "queue_count": state.get("queue_count"),
        "queue_text": state.get("queue_text"),
        "observation": state["observation"],
    }
    try:
        payload["wx_app_name"] = app.GetAppName()
        payload["wx_local_data_dir"] = str(wx.StandardPaths.Get().GetUserLocalDataDir())
    except Exception:
        pass
    if error:
        payload["error"] = error

    def write_payload():
        try:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except Exception:
            state["result"] = "FAIL"

    write_payload()
    smoke_session = state.get("smoke_session")
    try:
        if smoke_session:
            smoke_session["ssh"].close()
    except Exception:
        pass
    # Keep the smoke's event loop alive long enough for wx deferred native
    # destruction to run before checking its top-level registry.
    try:
        app.SetExitOnFrameDelete(False)
    except Exception:
        pass
    try:
        frame.Close()
    except Exception:
        pass
    ssh = smoke_session.get("ssh") if smoke_session else None
    observation = state["observation"]
    observation["transport_closed"] = bool(
        ssh is not None
        and ssh.client is None
        and ssh.sftp is None
        and ssh._shell_session is None
    )
    observation["cleanup_callbacks_drained"] = bool(
        lifecycle.cleanup_complete and not lifecycle.cleanup_timed_out
    )
    # Diagnostic only: no exception messages, profile names, or credentials.
    observation["cleanup_failures"] = list(
        getattr(lifecycle, "cleanup_failures", ())
    )
    # A wx.Frame with child WebView2 controllers may survive multiple idle
    # turns after Destroy() is requested. Never treat the request as a PASS:
    # probe actual removal, with a finite 1.3 s budget (100 + 24 * 50 ms).
    max_probes = 25

    def observe_destroy_and_exit():
        count = int(observation.get("frame_destroy_poll_count", 0)) + 1
        observation["frame_destroy_poll_count"] = count
        gone = _frame_destroyed(wx, frame)
        observation["frame_destroyed"] = gone
        if not gone and count < max_probes:
            try:
                wx.CallLater(50, observe_destroy_and_exit)
                return
            except Exception:
                # Missing native timer: keep FAIL and stop after persistence.
                pass
        observation["frame_destroy_budget_exhausted"] = not gone
        # Diagnostic only: actual Destroy() call outcome and native delete
        # state. These fields do NOT contribute to PASS independently.
        observation["frame_destroy_invoked"] = bool(
            getattr(frame, "_wx_shell_destroy_invoked", False)
        )
        observation["frame_destroy_return"] = getattr(
            frame, "_wx_shell_destroy_return", None
        )
        observation["frame_destroy_error_type"] = getattr(
            frame, "_wx_shell_destroy_error_type", None
        )
        try:
            observation["frame_is_being_deleted"] = bool(frame.IsBeingDeleted())
        except Exception as exc:
            observation["frame_is_being_deleted"] = type(exc).__name__
        write_payload()
        app.ExitMainLoop()

    try:
        wx.CallLater(100, observe_destroy_and_exit)
    except Exception:
        observe_destroy_and_exit()
    try:
        wx.CallLater(2000, app.ExitMainLoop)
    except Exception:
        pass
