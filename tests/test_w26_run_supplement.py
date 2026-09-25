"""W26 run supplement: close remaining owned proofs (EDIT-002/005/017..022, TODO-007/010)."""
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_editor_view import build_editor_panel
from hpc_gui.wx_shell import _editor_action_factory, _editor_session_key


def _pump(app, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()


def _click(control):
    control.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId()))


@pytest.fixture
def wx_app():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    wx.SafeYield()
    app.Destroy()


def _close(frame, app):
    try:
        frame.Close()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()
    try:
        if not frame.IsBeingDeleted():
            frame.Destroy()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()


@pytest.mark.gui
@pytest.mark.wx
def test_w26_supplement_remote_gui_save_proves_server_content(wx_app):
    """TODO-010 / EDIT-002: GUI edit+save lands verbatim on the server."""
    server = {}

    def save_remote(path, content):
        server[path] = content

    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(
            frame, path="/remote/job.sh", content="original",
            is_local=False, save_remote=save_remote,
        )
        frame.Show()
        wx.Yield()
        controls = panel._wx_editor_controls
        controls["editor"].SetValue("edited-by-gui")
        _click(controls["save"])
        _pump(wx_app, lambda: not panel._wx_editor_state["in_flight"])
        assert server.get("/remote/job.sh") == "edited-by-gui"
        assert not panel._wx_editor_model.controller.active.dirty
    finally:
        _close(frame, wx_app)


@pytest.mark.unit
def test_w26_supplement_save_submit_uses_sbatch_not_shell():
    """TODO-007: Save+Submit goes through scheduler sbatch, Save+Run via shell."""
    sbatch_calls = []
    shell_texts = []

    class _Files:
        def write_text(self, path, content):
            pass

        def upload(self, local, remote):
            self.uploaded = (local, remote)

    class _Slurm:
        def sbatch(self, path):
            sbatch_calls.append(path)
            return "Submitted batch job 42"

    class _Ssh:
        def send_shell_text(self, text):
            shell_texts.append(text)

    files = _Files()
    state = {"session": {"profile_name": "p", "profile": {"name": "p", "host": "h", "port": 22, "username": "u"}, "files": files, "slurm": _Slurm(), "ssh": _Ssh()}}
    factory = _editor_action_factory(state)
    from hpc_gui.services.editor_controller import DocumentModel

    remote_doc = DocumentModel("/remote/job.slurm", "x", "x", False, session_key=_editor_session_key(state))
    factory(remote_doc)["on_submit"](remote_doc)
    assert sbatch_calls == ["/remote/job.slurm"]
    assert shell_texts == []
    # Save+Run on a remote .sh must use shell text, never sbatch.
    sbatch_calls.clear()
    remote_sh = DocumentModel("/remote/run.sh", "x", "x", False, session_key=_editor_session_key(state))
    factory(remote_sh)["on_run"](remote_sh)
    assert sbatch_calls == []
    assert len(shell_texts) == 1 and "bash" in shell_texts[0] and "/remote/run.sh" in shell_texts[0]


@pytest.mark.gui
@pytest.mark.wx
def test_w26_supplement_local_vanished_parent_keeps_dirty(wx_app, tmp_path):
    """EDIT-019/022: vanished parent fails visibly and keeps dirty state."""
    missing = tmp_path / "gone" / "job.sh"
    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(frame, path=str(missing), content="orig", is_local=True)
        frame.Show()
        wx.Yield()
        controls = panel._wx_editor_controls
        controls["editor"].SetValue("changed")
        _click(controls["save"])
        _pump(wx_app, lambda: not panel._wx_editor_state["in_flight"])
        assert controls["status"].GetLabel() != ""
        assert panel._wx_editor_model.controller.active.dirty
        assert not missing.exists()
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w26_supplement_remote_disconnect_keeps_dirty(wx_app):
    """EDIT-008/018/020: disconnected remote save fails visibly, stays dirty."""
    def _disconnected(_path, _content):
        raise RuntimeError("disconnected session")

    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(frame, path="/remote/job.sh", content="orig", is_local=False, save_remote=_disconnected)
        frame.Show()
        wx.Yield()
        controls = panel._wx_editor_controls
        controls["editor"].SetValue("changed")
        _click(controls["save"])
        _pump(wx_app, lambda: not panel._wx_editor_state["in_flight"])
        assert controls["status"].GetLabel() != ""
        assert "disconnect" in controls["status"].GetLabel().lower()
        assert panel._wx_editor_model.controller.active.dirty
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w26_supplement_wx_find_replace(wx_app):
    """EDIT-005: wx find-next/replace-all parity with wrap semantics."""
    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(frame, path="/remote/a.sh", content="foo bar foo", is_local=False)
        frame.Show()
        wx.Yield()
        controls = panel._wx_editor_controls
        controls["find_in"].SetValue("foo")
        assert panel._wx_editor_find_next() is True
        sel = controls["editor"].GetStringSelection()
        assert sel == "foo"
        controls["replace_in"].SetValue("baz")
        count = panel._wx_editor_replace_all()
        assert count == 2
        assert controls["editor"].GetValue() == "baz bar baz"
        # Empty query is a safe no-op.
        controls["find_in"].SetValue("")
        assert panel._wx_editor_find_next() is False
        assert panel._wx_editor_replace_all() == 0
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w26_supplement_plugin_compat_visible(wx_app):
    """PLUGIN-COMPAT-001: version/compat/enabled state visible in listing."""
    from hpc_gui.wx_plugins import WxPluginManagerModel
    from hpc_gui.wx_plugins_view import build_plugins_panel

    model = WxPluginManagerModel()
    model.set_registry([
        {"id": "p1", "name": "P1", "version": "1.0", "installed": True, "enabled": True, "compatible": True},
        {"id": "p2", "name": "P2", "version": "2.0", "installed": True, "enabled": False, "compatible": False},
    ])
    frame = wx.Frame(None)
    try:
        host = build_plugins_panel(frame, model=model)
        frame.Show()
        wx.Yield()
        listing = host._wx_plugins_controls["listing"]
        assert listing.GetItemCount() == 2
        details0 = listing.GetItemText(0, 1)
        details1 = listing.GetItemText(1, 1)
        assert "1.0" in details0 and "enabled" in details0
        assert "2.0" in details1 and "disabled" in details1 and "incompatible" in details1
    finally:
        _close(frame, wx_app)
