"""wx fresh-user acceptance smoke flow"""
from __future__ import annotations

from pathlib import Path
import json
import os
from hpc_gui.core.i18n import current_language, load_saved_language, set_language, subscribe_language_change, system_default_language, t, unsubscribe_language_change
from hpc_gui.wx_shell_smoke_session import _connect_packaged_smoke_session


_FRESH_USER_RUN1_CHECKS = (
    "fresh_config_root",
    "first_run_empty_state",
    "profile_via_visible_controls",
    "loopback_success_via_controls",
    "safe_visible_failure",
    "persisted_nonsecret_state",
    "no_src_leakage",
    "clean_shutdown",
)


_FRESH_USER_RUN2_CHECKS = (
    "relaunch_state_present",
    "relaunch_no_src_leakage",
    "clean_shutdown",
)


_FRESH_PROFILE_NAME = "fresh-user-loopback"


_FRESH_DEAD_PROFILE_NAME = "fresh-user-dead-port"


def _run_fresh_user_acceptance(app, frame, session_state, output_path, lifecycle=None):
    """PKG-GJ-01 in-app phase: first-run from an isolated root via visible controls.

    Runs instead of the PTY surface smoke when ``HPC_GUI_FRESH_USER=1``.
    ``HPC_GUI_FRESH_RUN=1`` performs the fresh launch; ``=2`` verifies the
    relaunch against state persisted to disk (never to process memory).
    """
    import sys
    import time
    import wx

    run_index = os.environ.get("HPC_GUI_FRESH_RUN", "1").strip() or "1"
    expected = _FRESH_USER_RUN1_CHECKS if run_index == "1" else _FRESH_USER_RUN2_CHECKS
    checks = {name: "FAIL" for name in expected}
    state = {"phase": "fresh-user", "result": "FAIL", "done": True, "checks": checks}
    details: dict = {}

    def finish(error=None):
        try:
            frame.Close()
            if "clean_shutdown" in checks:
                checks["clean_shutdown"] = "PASS"
                # Shutdown is proven only at close time, after mark_all ran:
                # recompute the verdict so a clean close is not reported FAIL.
                if error is None and all(v == "PASS" for v in checks.values()):
                    state["result"] = "PASS"
        except Exception as exc:
            details["close"] = f"{type(exc).__name__}"
        payload = {
            "schema": "wx-fresh-user-runtime/1",
            "result": state["result"],
            "checks": checks,
            "details": details,
            "run": run_index,
        }
        try:
            from hpc_gui.core.paths import app_data_dir as _add
            details["app_data_dir"] = str(_add())
        except Exception:
            pass
        details["frozen"] = bool(getattr(sys, "frozen", False))
        details["executable"] = sys.executable
        try:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except Exception:
            state["result"] = "FAIL"
        wx.CallLater(50, app.ExitMainLoop)

    def mark_all():
        state["result"] = "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL"

    try:
        from hpc_gui.core.paths import app_data_dir, isolated_config_root

        fresh_root = app_data_dir()
        want = isolated_config_root()
        details["fresh_root"] = str(fresh_root)
        if "fresh_config_root" in checks:
            if want is not None and fresh_root == want and fresh_root.is_dir():
                checks["fresh_config_root"] = "PASS"
            else:
                details["fresh_root_mismatch"] = f"want={want} got={fresh_root}"

        from hpc_gui.config.storage import load_profiles

        config_path = fresh_root / "config.json"
        if run_index == "1":
            started_empty = load_profiles() == []
            if config_path.exists():
                # Parent guarantees no config.json before launch; an incidental
                # startup write is acceptable only when it carries no profiles.
                try:
                    started_empty = started_empty and json.loads(
                        config_path.read_text(encoding="utf-8")).get("profiles", []) == []
                except Exception:
                    started_empty = False
            if started_empty:
                checks["first_run_empty_state"] = "PASS"
            else:
                details["first_run"] = "config root was not clean at first launch"
        else:
            try:
                on_disk = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception as exc:
                details["relaunch"] = f"unreadable config: {type(exc).__name__}"
                on_disk = {}
            names = [p.get("name") for p in on_disk.get("profiles", []) if isinstance(p, dict)]
            secrets = [
                n for p in on_disk.get("profiles", []) if isinstance(p, dict)
                for n in ("password", "password_enc", "password_dpapi", "password_keychain_ref")
                if p.get(n)
            ]
            if _FRESH_PROFILE_NAME in names and not secrets:
                checks["relaunch_state_present"] = "PASS"
            else:
                details["relaunch"] = f"profiles={names} secrets={bool(secrets)}"

        leak = _fresh_src_leakage()
        if leak is None and ("no_src_leakage" in checks or "relaunch_no_src_leakage" in checks):
            checks["no_src_leakage" if run_index == "1" else "relaunch_no_src_leakage"] = "PASS"
        elif leak is not None:
            details["src_leakage"] = leak

        if run_index == "1":
            # Continue into the visible-control flow; individual marks decide.
            _fresh_run1_visible_flow(frame, session_state, lifecycle, checks, details)
        mark_all()
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}: {exc}"
        mark_all()
    finish(details.get("error"))
    return state


def _fresh_src_leakage():
    """Return None when the app resolves code from the bundle, else a reason."""
    import sys

    try:
        import hpc_gui
        module_file = Path(hpc_gui.__file__).resolve()
    except Exception as exc:
        return f"unresolvable hpc_gui: {type(exc).__name__}"
    if bool(getattr(sys, "frozen", False)):
        meipass = Path(getattr(sys, "_MEIPASS", "") or "")
        try:
            meipass = meipass.resolve()
        except Exception:
            pass
        if not meipass or meipass not in module_file.parents:
            return f"frozen module outside bundle: {module_file}"
        return None
    if "PYTHONPATH" in os.environ:
        return "PYTHONPATH present in non-frozen run"
    return None


def _fresh_find_button(root, name):
    import wx

    for child in root.GetChildren():
        if isinstance(child, wx.Button) and child.GetName() == name:
            return child
        found = _fresh_find_button(child, name)
        if found is not None:
            return found
    return None


def _fresh_click(button):
    import wx

    evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
    button.GetEventHandler().ProcessEvent(evt)


def _fresh_drive_add_dialog(panel_host, *, name, host, port, username):
    """Click the real AddConnection button and complete the real modal dialog.

    Returns True when the dialog saved (not cancelled) via its real Save path.
    """
    import wx

    import hpc_gui.wx_connection_dialog as dlg_mod
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

    captured: dict = {}
    real_cls = WxConnectionDialog

    class _Capture(real_cls):  # observe only; dialog behavior untouched
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured["dlg"] = self

    dlg_mod.WxConnectionDialog = _Capture
    try:
        add_btn = _fresh_find_button(panel_host, "AddConnection")
        if add_btn is None:
            return False
        saved = {"value": False}

        def autofill():
            dlg = captured.get("dlg")
            if dlg is None:
                wx.CallLater(200, autofill)
                return
            try:
                dlg.profile_name_ctrl.SetValue(name)
                dlg.host_ctrl.SetValue(host)
                dlg.port_ctrl.SetValue(str(port))
                dlg.username_ctrl.SetValue(username)
                try:
                    dlg.password_ctrl.SetValue("")
                except Exception:
                    pass
            except Exception:
                return
            _fresh_click(dlg.btn_save)

        def watchdog():
            if not saved["value"]:
                for win in wx.GetTopLevelWindows():
                    try:
                        if win is not panel_host and hasattr(win, "EndModal"):
                            win.EndModal(wx.ID_CANCEL)
                    except Exception:
                        pass

        # Wrap on_save observation via the panel refresh: poll ListBox after.
        wx.CallLater(500, autofill)
        wx.CallLater(30000, watchdog)
        _fresh_click(add_btn)
        # After the modal closes, check the visible list + disk state.
        try:
            from hpc_gui.config.storage import load_profiles
            live = [p.get("name") for p in load_profiles()]
            saved["value"] = name in live
        except Exception:
            saved["value"] = False
        return saved["value"]
    finally:
        dlg_mod.WxConnectionDialog = real_cls


def _fresh_run1_visible_flow(frame, session_state, lifecycle, checks, details):
    """Create-then-connect through visible panel controls; then fail safely."""
    import time
    import wx

    from hpc_gui.config.storage import load_profiles
    from hpc_gui.wx_connection import build_connection_panel

    loop_host = os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_HOST", "127.0.0.1").strip()
    try:
        loop_port = int(os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_PORT", "22"))
    except (TypeError, ValueError):
        details["visible_flow"] = "invalid loopback port env"
        return
    loop_user = os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_USER", "").strip()
    if not loop_user:
        details["visible_flow"] = "loopback user env missing"
        return

    def transient_connect(profile):
        return _connect_packaged_smoke_session(
            session_state, frame, lifecycle,
            host=str(profile.get("host") or ""),
            port=profile.get("port"),
            username=str(profile.get("username") or ""),
            profile_name=str(profile.get("name") or "fresh-user"),
        )

    panel_host = build_connection_panel(frame, profiles=[], connect=transient_connect)

    def listbox_strings():
        found = []

        def collect(node):
            for child in node.GetChildren():
                if isinstance(child, wx.ListBox):
                    found.extend(child.GetStrings())
                collect(child)

        collect(panel_host)
        return found

    def select_profile(target):
        boxes = []

        def collect(node):
            for child in node.GetChildren():
                if isinstance(child, wx.ListBox):
                    boxes.append(child)
                collect(child)

        collect(panel_host)
        for box in boxes:
            if box.FindString(target) != wx.NOT_FOUND:
                box.SetStringSelection(target)
                box.GetEventHandler().ProcessEvent(
                    wx.CommandEvent(wx.EVT_LISTBOX.typeId, box.GetId())
                )
                return True
        return False

    def status_texts():
        texts = []
        stack = [panel_host]
        while stack:
            node = stack.pop()
            if isinstance(node, wx.StaticText):
                texts.append(node.GetLabel())
            stack.extend(node.GetChildren())
        return texts

    def wait_for(predicate, timeout_s, pump=True):
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if predicate():
                return True
            if pump:
                wx.YieldIfNeeded()
            time.sleep(0.1)
        return predicate()

    # 1. Profile creation through AddConnection -> modal dialog -> Save.
    created = _fresh_drive_add_dialog(
        panel_host, name=_FRESH_PROFILE_NAME,
        host=loop_host, port=loop_port, username=loop_user,
    )
    if created and _FRESH_PROFILE_NAME in listbox_strings():
        checks["profile_via_visible_controls"] = "PASS"
    else:
        details["visible_flow"] = "AddConnection dialog did not persist the profile"
        return

    # 2. Loopback success through ListBox selection + ConnectSelected click.
    connect_btn = _fresh_find_button(panel_host, "ConnectSelected")
    if connect_btn is None or not select_profile(_FRESH_PROFILE_NAME):
        details["visible_flow"] = "cannot select the fresh profile"
        return
    _fresh_click(connect_btn)
    if wait_for(lambda: any(
        "onnected" in t and "isconnect" not in t and "onnecting" not in t
        for t in status_texts()
    ), 60):
        checks["loopback_success_via_controls"] = "PASS"
    else:
        details["visible_flow"] = f"loopback did not connect: {status_texts()[:4]}"
        return

    # 3. Safe visible failure: dead-port profile selected + connected attempt.
    from hpc_gui.config.storage import upsert_profile

    upsert_profile({"name": _FRESH_DEAD_PROFILE_NAME, "host": "127.0.0.1",
                    "port": 1, "username": loop_user})
    try:
        panel_host2 = build_connection_panel(
            frame, profiles=load_profiles(), connect=transient_connect)
        boxes = []

        def collect2(node):
            for child in node.GetChildren():
                if isinstance(child, wx.ListBox):
                    boxes.append(child)
                collect2(child)

        collect2(panel_host2)
        dead_selected = False
        for box in boxes:
            if box.FindString(_FRESH_DEAD_PROFILE_NAME) != wx.NOT_FOUND:
                box.SetStringSelection(_FRESH_DEAD_PROFILE_NAME)
                box.GetEventHandler().ProcessEvent(
                    wx.CommandEvent(wx.EVT_LISTBOX.typeId, box.GetId()))
                dead_selected = True
        dead_btn = _fresh_find_button(panel_host2, "ConnectSelected")

        def dead_texts():
            texts = []
            stack = [panel_host2]
            while stack:
                node = stack.pop()
                if isinstance(node, wx.StaticText):
                    texts.append(node.GetLabel())
                stack.extend(node.GetChildren())
            return texts

        if dead_selected and dead_btn is not None:
            _fresh_click(dead_btn)
            failed = wait_for(lambda: any("ail" in t for t in dead_texts()), 60)
            still_ok = any(
                "onnected" in t and "isconnect" not in t and "onnecting" not in t and "ail" not in t
                for t in dead_texts()
            )
            if failed and not still_ok:
                checks["safe_visible_failure"] = "PASS"
            else:
                details["visible_flow"] = f"dead-port failure not visible: {dead_texts()[:4]}"
        else:
            details["visible_flow"] = "cannot drive dead-port profile selection"
    finally:
        try:
            from hpc_gui.config.storage import delete_profile
            delete_profile(_FRESH_DEAD_PROFILE_NAME)
        except Exception:
            pass

    # 4. Persisted non-secret state proven from disk bytes, not memory.
    try:
        from hpc_gui.core.paths import app_data_dir as _fresh_app_data_dir

        raw = (_fresh_app_data_dir() / "config.json").read_text(encoding="utf-8")
        on_disk = json.loads(raw)
    except Exception as exc:
        details["visible_flow"] = f"config unreadable: {type(exc).__name__}"
        return
    stored = [p for p in on_disk.get("profiles", [])
              if isinstance(p, dict) and p.get("name") == _FRESH_PROFILE_NAME]
    secret_keys = ("password", "password_enc", "password_dpapi", "password_keychain_ref")
    if stored and not any(stored[0].get(k) for k in secret_keys):
        checks["persisted_nonsecret_state"] = "PASS"
    else:
        details["visible_flow"] = "fresh profile missing from disk or carries a secret"
