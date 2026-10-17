"""W04 support matrix acceptance tests: file actions."""

import pytest
import pathlib
import re
import time
import hpc_gui.wx_shell as wx_shell
from hpc_gui.core.i18n import t
from hpc_gui.core.i18n import load_language
from w04_support_freeze_support import _MessageBoxCapture, _auto_cancel_native_selectors, _close_shell, wx


@pytest.fixture(autouse=True)
def _english_bundle():
    load_language("en")
    yield
    load_language("en")


@pytest.fixture
def wx_app():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        try:
            if window:
                window.Destroy()
        except Exception:
            pass
    app.ProcessPendingEvents()
    wx.SafeYield()
    app.Destroy()


def test_local_delete__requires_explicit_destructive_confirm(wx_app, tmp_path, monkeypatch):
    """TRUTH-070: Delete carries YES_NO + ICON_WARNING confirmation and only
    then mutates; the label implies exactly this destructive semantic."""
    from hpc_gui.wx_local_files import show_local_files

    target = tmp_path / "doomed.txt"
    target.write_text("x", encoding="utf-8")
    keeper = tmp_path / "keeper.txt"
    keeper.write_text("y", encoding="utf-8")

    styles = []

    def _recorder(*args, **kwargs):
        style = args[2] if len(args) > 2 else kwargs.get("style", 0)
        styles.append(style)
        return wx.YES

    monkeypatch.setattr(wx, "MessageBox", _recorder)
    show_local_files(path=tmp_path)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    wx_app.ProcessPendingEvents()
    listing = frame._wx_local_controls["listing"]
    row = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "doomed.txt")
    listing.Select(row)
    frame._wx_local_run_action("delete")

    def _settled():
        return not frame._wx_local_state["mutation_in_flight"]

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        wx_app.ProcessPendingEvents()
        if _settled():
            break
        wx.MilliSleep(5)
    assert _settled()
    assert styles, "delete must confirm before mutating"
    assert any(s & wx.YES_NO and s & wx.ICON_WARNING for s in styles), styles
    assert not target.exists()
    assert keeper.exists()


def test_remote_delete__confirm_is_destructive_styled():
    """TRUTH-070 (remote leg, source-anchored): the remote delete confirm
    call site carries the same YES_NO + ICON_WARNING semantics."""
    source = pathlib.Path("src/hpc_gui/wx_remote_files_view.py").read_text(encoding="utf-8")
    match = re.search(r'dirs\.delete_confirm".*?YES_NO\s*\|\s*wx\.ICON_WARNING', source, re.DOTALL)
    assert match, "remote delete_confirm call site must carry YES_NO + ICON_WARNING"


def test_remote_context__allowed_actions_resolve_to_labels():
    """Dead-key guard for context surfaces: every remote-allowed action
    resolves to a real label in the bundle (no [dirs.x] masking)."""
    from hpc_gui.services.file_context_actions import (
        FILE_CONTEXT_LABEL_KEYS,
        context_selection,
        visible_actions,
    )

    selection = context_selection("/remote/home", False, ("/remote/home",), (False,))
    for action in visible_actions(selection, remote=True):
        key = FILE_CONTEXT_LABEL_KEYS.get(action, f"dirs.{action}")
        assert t(key) != f"[{key}]", f"unresolved label for remote action {action!r}"


def test_header_upload_download__use_panel_run_actions(wx_app, monkeypatch):
    """TRUTH-069: header Upload/Download funnel into the same panel
    run_action paths the browser toolbars use (one truthful transfer path)."""
    _MessageBoxCapture(monkeypatch)
    _auto_cancel_native_selectors(monkeypatch)
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        pages = frame._wx_shell_controls["pages"]["NAV-FILES"]
        local_panel, remote_panel = pages["local"], pages["remote"]
        seen = []

        orig_local = local_panel._wx_local_run_action
        orig_remote = remote_panel._wx_remote_run_action

        def _local_rec(action, *args, **kwargs):
            seen.append(("local", action))
            return orig_local(action, *args, **kwargs)

        def _remote_rec(action, *args, **kwargs):
            seen.append(("remote", action))
            return orig_remote(action, *args, **kwargs)

        local_panel._wx_local_run_action = _local_rec
        remote_panel._wx_remote_run_action = _remote_rec
        try:
            upload_btn, download_btn = pages["upload_selected"], pages["download_selected"]
            upload_btn.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, upload_btn.GetId()))
            download_btn.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, download_btn.GetId()))
            wx.Yield()
        finally:
            local_panel._wx_local_run_action = orig_local
            remote_panel._wx_remote_run_action = orig_remote
        assert ("local", "upload") in seen, f"header upload must call local run_action: {seen}"
        assert ("remote", "download") in seen, f"header download must call remote run_action: {seen}"
    finally:
        _close_shell(frame)
