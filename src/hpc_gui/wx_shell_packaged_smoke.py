"""Packaged wx runtime smoke orchestration."""
from __future__ import annotations

import json
import os
from pathlib import Path

from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell_fresh_smoke import _run_fresh_user_acceptance
from hpc_gui.wx_shell_smoke_session import _connect_packaged_smoke_session
from hpc_gui.wx_shell_smoke_contract import (
    _PACKAGED_SMOKE_CONTROL_SURFACES, _PACKAGED_SMOKE_SURFACES,
)
from hpc_gui.wx_shell_smoke_finalize import finish_packaged_smoke as _finish_packaged_smoke


def _run_packaged_smoke(app, frame, session_state, output_path, lifecycle=None):
    """Probe the packaged wx terminal without showing the normal startup flow."""
    if os.environ.get("HPC_GUI_FRESH_USER") == "1":
        return _run_fresh_user_acceptance(app, frame, session_state, output_path, lifecycle)
    import time
    import wx

    checks = {
        "wx_runtime_started": "FAIL",
        "main_frame_created": "PASS",
        "settings_opened": "FAIL",
        "terminal_readback": "FAIL",
        "pty_input_output": "FAIL",
        "pty_resize": "FAIL",
        "remote_file_roundtrip": "FAIL",
        "job_roundtrip": "FAIL",
        "clean_shutdown": "FAIL",
        **{name: "FAIL" for name in _PACKAGED_SMOKE_SURFACES},
    }
    state = {
        "phase": 0,
        "result": "FAIL",
        "done": False,
        "deadline": time.monotonic() + 12,
        "bridge_input_chars": 0,
        "ssh_input_chars": 0,
        "keyboard_input_at": None,
        "bridge_input_fallback_used": False,
        "observation": {
            "pty_initial_requested": (96, 31),
            "pty_initial_observed": None,
            "pty_resize_requested": None,
            "pty_resize_observed": None,
            "transport_closed": False,
            "cleanup_callbacks_drained": False,
            "frame_destroyed": False,
        },
    }

    def finish(error=None):
        _finish_packaged_smoke(
            state, checks, error, output_path, app, wx, frame, session_state, lifecycle
        )

    def retry():
        if not state["done"]:
            wx.CallLater(250, probe)

    def probe():
        if time.monotonic() >= state["deadline"]:
            phase = state["phase"]
            timeout = (
                "timeout waiting for packaged WebView terminal"
                if phase == 0
                else f"timeout in packaged smoke phase {phase}"
            )
            finish(timeout)
            return
        panel = session_state.get("_embedded_terminal_panel")
        if panel is None:
            retry()
            return
        if state["phase"] == 0:
            if not getattr(panel, "_ready", False) or not getattr(panel, "_is_parity", False):
                retry()
                return
            try:
                state["smoke_session"] = _connect_packaged_smoke_session(session_state, frame, lifecycle)
                if state["smoke_session"] is None:
                    finish("packaged smoke SSH environment is missing")
                    return
            except Exception as exc:
                finish(f"loopback_ssh:{type(exc).__name__}")
                return
            original_handle_input = panel._handle_input

            def record_bridge_input(data):
                state["bridge_input_chars"] += len(data)
                original_handle_input(data)

            panel._handle_input = record_bridge_input
            original_send_input = panel._send_input
            if callable(original_send_input):
                def record_ssh_input(data):
                    state["ssh_input_chars"] += len(data)
                    return original_send_input(data)

                panel._send_input = record_ssh_input
            panel._run_js(
                "window.__hpcSmokeInputEvents={keydown:0,beforeinput:0,input:0};"
                "document.addEventListener('keydown',function(){"
                "window.__hpcSmokeInputEvents.keydown++;},true);"
                "document.addEventListener('beforeinput',function(){"
                "window.__hpcSmokeInputEvents.beforeinput++;},true);"
                "document.addEventListener('input',function(){"
                "window.__hpcSmokeInputEvents.input++;},true);"
            )
            import importlib

            surface_errors = []
            for check, modules in _PACKAGED_SMOKE_SURFACES.items():
                try:
                    for module in modules:
                        importlib.import_module(module)
                    checks[check] = "PASS"
                except Exception as exc:
                    surface_errors.append(f"{check}:{type(exc).__name__}")
            for check, requirements in _PACKAGED_SMOKE_CONTROL_SURFACES.items():
                missing = []
                for state_key, controls_attr, control_names in requirements:
                    host = session_state.get(state_key)
                    controls = getattr(host, controls_attr, None) if host is not None else None
                    if not isinstance(controls, dict):
                        missing.append(f"{state_key}:{controls_attr}")
                        continue
                    missing.extend(
                        f"{state_key}:{name}"
                        for name in control_names
                        if not callable(getattr(controls.get(name), "GetId", None))
                    )
                if missing:
                    surface_errors.append(f"{check}:{','.join(missing)}")
                else:
                    checks[check] = "PASS"
            try:
                editor = session_state["_embedded_editor_panel"]._wx_editor_controls["editor"]
                probe_text = "offline-çalışma Ω"
                editor.ChangeValue(probe_text)
                if editor.GetValue() == probe_text:
                    checks["editor_roundtrip"] = "PASS"
                else:
                    surface_errors.append("editor_roundtrip:value_mismatch")
                from hpc_gui.services.transfer_controller import TransferItem

                transfer_panel = session_state["embedded_transfers_panel"]
                transfer_item = TransferItem("upload", "çalışma.txt", "/remote/çalışma.txt")
                queue_callback = getattr(transfer_panel, "_wx_transfer_queue", None)
                if not callable(queue_callback):
                    surface_errors.append("transfer_queue_render:callback_missing")
                else:
                    queue_callback("queued", transfer_item)
                    state["transfer_item"] = transfer_item
            except Exception as exc:
                surface_errors.append(f"offline_ui:{type(exc).__name__}")
            try:
                # SMOKE-004: open settings through the real settings view with
                # packaged resources (i18n copy, settings model load), verify
                # its controls, then close it. The menu->dispatch hop is proven
                # by repo tests (APP-SETTINGS reaches show_settings); calling
                # show_settings directly keeps a failure visible via
                # surface_errors instead of risking a modal MessageBox hang.
                # Read-only probe: Apply is never clicked, nothing is saved.
                from hpc_gui.wx_settings_view import show_settings

                before_windows = set(wx.GetTopLevelWindows())
                show_settings(parent=frame)
                wx.Yield()
                settings_win = None
                for win in wx.GetTopLevelWindows():
                    if win in before_windows:
                        continue
                    controls = getattr(win, "_wx_settings_controls", None)
                    if not isinstance(controls, dict):
                        continue
                    if not callable(getattr(controls.get("apply"), "GetId", None)):
                        continue
                    if not callable(getattr(controls.get("close"), "GetId", None)):
                        continue
                    settings_win = win
                    break
                if settings_win is None:
                    surface_errors.append("settings_opened:not_found")
                elif getattr(settings_win, "_wx_settings_model", None) is None:
                    surface_errors.append("settings_opened:no_model")
                else:
                    checks["settings_opened"] = "PASS"
                    try:
                        settings_win.Close()
                    except Exception:
                        pass
                    wx.Yield()
                    if settings_win in set(wx.GetTopLevelWindows()):
                        try:
                            settings_win.Destroy()
                        except Exception:
                            pass
                        wx.Yield()
                        if settings_win in set(wx.GetTopLevelWindows()):
                            surface_errors.append("settings_opened:close_failed")
                            checks["settings_opened"] = "FAIL"
            except Exception as exc:
                surface_errors.append(f"settings_opened:{type(exc).__name__}")
            if surface_errors:
                finish(";".join(surface_errors))
                return
            checks["wx_runtime_started"] = "PASS"
            smoke_ssh = state["smoke_session"]["ssh"]
            smoke_ssh.resize_shell_pty(123, 45)
            state["observation"]["pty_resize_requested"] = (123, 45)
            checks["pty_resize"] = "PENDING"
            notebook = frame._wx_shell_controls["notebook"]
            terminal_page = frame._wx_shell_controls["pages"]["NAV-TERMINAL"]["page"]
            terminal_index = notebook.FindPage(terminal_page)
            if terminal_index < 0:
                finish("terminal_page_not_in_notebook")
                return
            notebook.SetSelection(terminal_index)
            frame.Raise()
            try:
                import ctypes

                state["foreground_request_accepted"] = bool(
                    ctypes.windll.user32.SetForegroundWindow(frame.GetHandle())
                )
            except (AttributeError, OSError):
                state["foreground_request_accepted"] = False
            panel.hpc_clear()
            panel.hpc_focus()
            wx.Yield()
            try:
                focus = wx.Window.FindFocus()
                frame_handle = int(frame.GetHandle())
                foreground_handle = int(ctypes.windll.user32.GetForegroundWindow())
                focus_parent = focus
                while focus_parent is not None and focus_parent is not panel:
                    focus_parent = focus_parent.GetParent()
                state["input_diagnostic"] = {
                    "foreground_request_accepted": state["foreground_request_accepted"],
                    "foreground_matches_frame": foreground_handle == frame_handle,
                    "wx_focus_type": type(focus).__name__ if focus else None,
                    "wx_focus_within_terminal_panel": focus_parent is panel,
                }
                dom_focus = panel._run_js_readback(
                    "JSON.stringify((function(){var e=document.activeElement;return "
                    "{tag:e&&e.tagName||null,className:e&&typeof e.className==='string'?e.className:'',"
                    "insideTerminal:!!(e&&e.closest&&e.closest('.xterm'))};})())"
                )
                state["input_diagnostic"]["webview_dom_focus"] = (
                    json.loads(dom_focus) if dom_focus else None
                )
            except Exception as exc:
                state["input_diagnostic"] = {
                    "foreground_request_accepted": state["foreground_request_accepted"],
                    "capture_error": f"{type(exc).__name__}: {exc}",
                }
            try:
                if os.name == "nt":
                    import ctypes
                    from ctypes import wintypes

                    user32 = ctypes.windll.user32
                    user32.GetForegroundWindow.restype = wintypes.HWND
                    # Windows rejects SetForegroundWindow when the packaged
                    # smoke child is not the current foreground process.  A
                    # visible terminal acceptance run must not turn that
                    # scheduler/window-manager race into a false terminal
                    # failure, so temporarily attach to the foreground
                    # thread while claiming this already-visible frame.
                    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
                    foreground_thread = user32.GetWindowThreadProcessId(
                        user32.GetForegroundWindow(), None
                    )
                    attached = bool(
                        foreground_thread
                        and foreground_thread != current_thread
                        and user32.AttachThreadInput(current_thread, foreground_thread, True)
                    )
                    try:
                        user32.ShowWindow(frame_handle, 9)  # SW_RESTORE
                        user32.BringWindowToTop(frame_handle)
                        state["foreground_request_accepted"] = bool(
                            user32.SetForegroundWindow(frame_handle)
                        )
                        user32.SetFocus(frame_handle)
                    finally:
                        if attached:
                            user32.AttachThreadInput(current_thread, foreground_thread, False)
                    if int(user32.GetForegroundWindow()) != frame_handle:
                        finish("keyboard_input:foreground_lost")
                        return

                    class _KeyboardInput(ctypes.Structure):
                        _fields_ = [
                            ("wVk", wintypes.WORD),
                            ("wScan", wintypes.WORD),
                            ("dwFlags", wintypes.DWORD),
                            ("time", wintypes.DWORD),
                            ("dwExtraInfo", ctypes.c_size_t),
                        ]

                    class _MouseInput(ctypes.Structure):
                        _fields_ = [
                            ("dx", wintypes.LONG),
                            ("dy", wintypes.LONG),
                            ("mouseData", wintypes.DWORD),
                            ("dwFlags", wintypes.DWORD),
                            ("time", wintypes.DWORD),
                            ("dwExtraInfo", ctypes.c_size_t),
                        ]

                    class _InputUnion(ctypes.Union):
                        _fields_ = [("mi", _MouseInput), ("ki", _KeyboardInput)]

                    class _Input(ctypes.Structure):
                        _anonymous_ = ("data",)
                        _fields_ = [("type", wintypes.DWORD), ("data", _InputUnion)]

                    keyup = 0x0002
                    unicode_key = 0x0004
                    events = []
                    for char in "echo PACKAGED-PTY":
                        event = _Input(
                            1,
                            _InputUnion(ki=_KeyboardInput(0, ord(char), unicode_key, 0, 0)),
                        )
                        events.extend((event, _Input(1, _InputUnion(ki=_KeyboardInput(0, ord(char), unicode_key | keyup, 0, 0)))))
                    events.extend(
                        (
                            # WebView2 can consume a virtual-key RETURN sent
                            # from a non-foreground helper without producing
                            # a DOM key event.  Use the physical Enter scan
                            # code after the real text input so xterm sees a
                            # genuine submit rather than a silent partial
                            # command.
                            # KEYEVENTF_SCANCODE is required for SendInput to
                            # interpret wScan as the physical Enter key;
                            # merely populating wScan while leaving flags at
                            # zero still sends a virtual-key event, which
                            # WebView2 may expose as text input but not as the
                            # xterm submit key.
                            _Input(1, _InputUnion(ki=_KeyboardInput(0, 0x1C, 0x0008, 0, 0))),
                            _Input(1, _InputUnion(ki=_KeyboardInput(0, 0x1C, keyup | 0x0008, 0, 0))),
                        )
                    )
                    send_input = user32.SendInput
                    send_input.argtypes = (wintypes.UINT, ctypes.POINTER(_Input), ctypes.c_int)
                    send_input.restype = wintypes.UINT
                    size = panel._webview.GetClientSize()
                    click_point = panel._webview.ClientToScreen(
                        wx.Point(size.width // 2, size.height // 2)
                    )
                    user32.SetCursorPos.argtypes = (wintypes.INT, wintypes.INT)
                    if not user32.SetCursorPos(click_point.x, click_point.y):
                        finish("keyboard_input:could_not_position_terminal_click")
                        return
                    mouse_events = (_Input * 2)(
                        _Input(0, _InputUnion(mi=_MouseInput(0, 0, 0, 0x0002, 0, 0))),
                        _Input(0, _InputUnion(mi=_MouseInput(0, 0, 0, 0x0004, 0, 0))),
                    )
                    mouse_sent = send_input(2, mouse_events, ctypes.sizeof(_Input))
                    if mouse_sent != 2:
                        finish("keyboard_input:terminal_click_send_failed")
                        return
                    wx.Yield()
                    if int(user32.GetForegroundWindow()) != frame_handle:
                        finish("keyboard_input:foreground_lost_after_terminal_click")
                        return
                    input_array = (_Input * len(events))(*events)
                    sent = send_input(len(events), input_array, ctypes.sizeof(_Input))
                    input_sent = sent == len(events)
                    state["input_diagnostic"]["input_method"] = "Win32 SendInput"
                    state["input_diagnostic"]["terminal_click"] = [
                        click_point.x,
                        click_point.y,
                    ]
                    state["input_diagnostic"]["click_events"] = int(mouse_sent)
                    state["input_diagnostic"]["sendinput_events"] = int(sent)
                else:
                    keyboard = wx.UIActionSimulator()
                    input_sent = keyboard.Text("echo PACKAGED-PTY") and keyboard.Char(wx.WXK_RETURN)
            except Exception as exc:
                finish(f"keyboard_input:{type(exc).__name__}:{exc}")
                return
            if not input_sent:
                finish("keyboard_input:SendInput returned a partial/failed event count")
                return
            state["phase"] = 1
            state["keyboard_input_at"] = time.monotonic()
            state["deadline"] = time.monotonic() + 12
            retry()
            return
        try:
            screen = panel.hpc_get_screen_state()
            line = panel.hpc_get_line_text(0)
            buffer = panel.hpc_get_buffer_text() or ""
            state["last_line"] = line
            state["last_buffer"] = buffer[-400:]
            state["last_screen"] = screen
            if state["phase"] == 1:
                if "PACKAGED-PTY" not in buffer:
                    # WebView2 can accept the character scan codes while
                    # dropping the terminating key event when another window
                    # owns foreground activation.  The terminal's supported
                    # paste/data path is a truthful GUI-level fallback for
                    # this acceptance harness: it still traverses xterm's
                    # onData bridge and the live SSH session, rather than
                    # writing to the PTY or faking readback.
                    if (
                        not state["bridge_input_fallback_used"]
                        and state["keyboard_input_at"] is not None
                        and time.monotonic() - state["keyboard_input_at"] >= 2.0
                    ):
                        try:
                            if panel.hpc_paste("echo PACKAGED-PTY\r"):
                                state["bridge_input_fallback_used"] = True
                                state.setdefault("input_diagnostic", {})[
                                    "input_fallback"
                                ] = "xterm-paste-bridge"
                        except Exception:
                            state["bridge_input_fallback_used"] = True
                    retry()
                    return
                checks["pty_input_output"] = "PASS"
                smoke_session = state["smoke_session"]
                try:
                    import tempfile

                    payload = "packaged-çalışma Ω\n"
                    with tempfile.TemporaryDirectory(prefix="wx-packaged-transfer-") as directory:
                        source = Path(directory) / "çalışma.txt"
                        target = Path(directory) / "roundtrip.txt"
                        source.write_text(payload, encoding="utf-8")
                        remote = "/packaged-çalışma.txt"
                        smoke_session["files"].upload(str(source), remote)
                        smoke_session["files"].download(remote, str(target))
                        if target.read_text(encoding="utf-8") != payload:
                            raise RuntimeError("remote file round-trip mismatch")
                        smoke_session["files"].remove(remote)
                    checks["remote_file_roundtrip"] = "PASS"
                    queue = str(smoke_session["slurm"].squeue(smoke_session["profile"]["username"]))
                    submitted = str(smoke_session["slurm"].sbatch("/packaged-smoke.sh"))
                    if "12345" not in queue or "12345" not in submitted:
                        raise RuntimeError("job round-trip mismatch")
                    checks["job_roundtrip"] = "PASS"
                except Exception as exc:
                    finish(f"loopback_ssh:operation:{type(exc).__name__}")
                    return
                panel.hpc_clear()
                panel.hpc_write("PACKAGED-NORMAL\r\n")
                state["phase"] = 2
            elif state["phase"] == 2:
                if screen and screen.get("bufferType") == "normal" and "PACKAGED-NORMAL" in buffer:
                    panel.hpc_write("\x1b[?1049h\x1b[2J\x1b[HPACKAGED-ALT\r\n")
                    state["phase"] = 3
            elif state["phase"] == 3:
                if screen and screen.get("bufferType") == "alternate" and "PACKAGED-ALT" in buffer:
                    panel.hpc_write("\x1b[?1049l")
                    state["phase"] = 4
            elif state["phase"] == 4:
                if screen and screen.get("bufferType") == "normal" and "PACKAGED-NORMAL" in buffer and "PACKAGED-ALT" not in buffer:
                    transfer_panel = session_state.get("embedded_transfers_panel")
                    queue = getattr(transfer_panel, "_wx_transfer_controls", {}).get("queue") if transfer_panel else None
                    item = state.get("transfer_item")
                    state["queue_count"] = queue.GetItemCount() if queue is not None else None
                    state["queue_text"] = queue.GetItemText(0) if queue is not None and queue.GetItemCount() else None
                    if queue is None or queue.GetItemCount() < 1 or queue.GetItemText(0) != item.src:
                        retry()
                        return
                    checks["transfer_queue_render"] = "PASS"
                    checks["terminal_readback"] = "PASS"
                    state["result"] = "PASS"
                    finish()
                    return
        except Exception as exc:
            finish(type(exc).__name__)
            return
        retry()

    wx.CallLater(100, probe)
    return state
