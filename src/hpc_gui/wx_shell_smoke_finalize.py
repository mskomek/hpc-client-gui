"""Finalize child-side wx smoke evidence after teardown readback."""
from __future__ import annotations

import json
from pathlib import Path


def _frame_destroyed(wx, frame) -> bool:
    """Observe actual top-level removal, not a pending Destroy() request.

    wxPython does not provide wx.IsDestroyed. A still-registered frame must
    never be reported as destroyed, even if shutdown callbacks have run.
    """
    try:
        return frame not in wx.GetTopLevelWindows()
    except Exception:
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
    # wx.Destroy() is deferred on some platforms. Sample after one bounded
    # event-loop turn; the parent still requires a zero exit and no timeout.
    def observe_destroy_and_exit():
        observation["frame_destroyed"] = _frame_destroyed(wx, frame)
        write_payload()
        app.ExitMainLoop()

    try:
        wx.CallLater(100, observe_destroy_and_exit)
    except Exception:
        # Missing timer/event loop is not a PASS: the registry decides.
        observe_destroy_and_exit()
    try:
        wx.CallLater(2000, app.ExitMainLoop)
    except Exception:
        pass
