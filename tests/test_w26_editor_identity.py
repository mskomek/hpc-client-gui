"""W26 focused tests: editor routing, document identity, and save targets.

Covers HPC-W06-EDIT-010..016 (document identity), HPC-W06-EDIT-013/021
(encoding/newline preservation and failure visibility), HPC-W06-EDIT-007
(binary/large guard), HPC-W06-TODO-039 (unicode/line endings), and the
HPC-W06-EDIT-016 connection-switch save-target guard.
"""
import time

import pytest

from hpc_gui.services.editor_controller import (
    DocumentModel,
    detect_newline,
    normalize_newlines_for_save,
)
from hpc_gui.wx_editor import WxEditorModel
from hpc_gui.wx_editor_view import editor_binary_guard_reason

wx = pytest.importorskip("wx")

from hpc_gui.wx_editor_view import build_editor_panel  # noqa: E402


@pytest.mark.unit
def test_w26_identity_same_path_distinct_sessions_are_distinct_tabs():
    model = WxEditorModel()
    first = model.open("/remote/job.sh", "a", session_key="profA|h|22|u")
    second = model.open("/remote/job.sh", "b", session_key="profB|h|22|u")
    assert first == 0 and second == 1
    assert len(model.controller.documents) == 2
    # Same identity selects the existing tab (duplicate suppression kept).
    assert model.open("/remote/job.sh", "ignored", session_key="profB|h|22|u") == 1
    assert len(model.controller.documents) == 2


@pytest.mark.unit
def test_w26_identity_local_vs_remote_same_path_are_distinct():
    model = WxEditorModel()
    assert model.open("/job.sh", "local", is_local=True) == 0
    assert model.open("/job.sh", "remote", is_local=False) == 1
    assert len(model.controller.documents) == 2


@pytest.mark.unit
def test_w26_newline_detect_and_normalize_round_trip():
    assert detect_newline("a\nb\n") == "\n"
    assert detect_newline("a\r\nb\r\n") == "\r\n"
    assert detect_newline("") == "\n"
    assert normalize_newlines_for_save("a\nb\n", "\r\n") == "a\r\nb\r\n"
    assert normalize_newlines_for_save("a\r\nb\r\n", "\n") == "a\nb\n"
    model = WxEditorModel()
    model.open("/remote/crlf.sh", "a\r\nb\r\n")
    assert model.controller.active.newline == "\r\n"


@pytest.mark.unit
def test_w26_binary_and_large_guard_reasons():
    assert editor_binary_guard_reason("/x.sh", "plain text") is None
    binary = editor_binary_guard_reason("/x.bin", "ab\x00cd")
    assert binary and "Binary" in binary
    big = editor_binary_guard_reason("/big.sh", "x" * (2 * 1024 * 1024 + 1))
    assert big and "large" in big.lower()


@pytest.mark.unit
def test_w26_unicode_content_preserved_in_model():
    text = "echo héllo wörld ☃\n# Türkçe yorum\n"
    model = WxEditorModel()
    model.open("/remote/uni.sh", text)
    assert model.controller.active.content == text
    assert "☃" in model.controller.active.content


@pytest.mark.unit
def test_w26_session_pin_refuses_save_to_wrong_host():
    from hpc_gui.wx_shell import _editor_action_factory

    calls = []
    state = {
        "session": {
            "profile_name": "lab",
            "profile": {"name": "lab", "host": "h1", "port": 22, "username": "u"},
            "files": type("F", (), {"write_text": lambda self, p, c: calls.append((p, c))})(),
            "slurm": None,
            "ssh": None,
        }
    }
    factory = _editor_action_factory(state)
    pinned = DocumentModel("/remote/job.sh", "x", "x", False, session_key="lab|h1|22|u")
    factory(pinned)["save_remote"]("/remote/job.sh", "x")
    assert calls == [("/remote/job.sh", "x")]
    # Switch connection: the pinned document must not save through it.
    state["session"] = {
        "profile_name": "other",
        "profile": {"name": "other", "host": "h2", "port": 22, "username": "u"},
        "files": type("F", (), {"write_text": lambda self, p, c: calls.append((p, c))})(),
        "slurm": None,
        "ssh": None,
    }
    with pytest.raises(RuntimeError) as exc_info:
        factory(pinned)["save_remote"]("/remote/job.sh", "x")
    # Locale-independent: the refusal must name the cause in any language
    # (English fallback or loaded locale), and nothing may be written.
    assert str(exc_info.value).strip() != ""
    assert len(calls) == 1


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
def test_w26_wx_crlf_local_save_preserves_line_endings(wx_app, tmp_path):
    target = tmp_path / "crlf.sh"
    target.write_bytes(b"a\r\nb\r\n")
    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(frame, path=str(target), content="a\r\nb\r\n", is_local=True)
        frame.Show()
        wx.Yield()
        controls = panel._wx_editor_controls
        controls["editor"].SetValue("a\r\nb\r\n")
        _click(controls["save"])
        _pump(wx_app, lambda: not panel._wx_editor_state["in_flight"])
        assert target.read_bytes() == b"a\r\nb\r\n"
        assert not panel._wx_editor_model.controller.active.dirty
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w26_wx_encoding_failure_keeps_dirty_and_reports(wx_app, tmp_path):
    target = tmp_path / "enc.sh"
    target.write_text("orig", encoding="utf-8")
    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(
            frame, path=str(target), content="orig", is_local=True, encoding="bogus-codec-xyz"
        )
        frame.Show()
        wx.Yield()
        controls = panel._wx_editor_controls
        controls["editor"].SetValue("changed")
        _click(controls["save"])
        _pump(wx_app, lambda: not panel._wx_editor_state["in_flight"])
        assert controls["status"].GetLabel() != ""
        assert panel._wx_editor_model.controller.active.dirty
        assert target.read_text(encoding="utf-8") == "orig"
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w26_wx_binary_content_refused_with_visible_diagnostic(wx_app):
    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(frame, path="/remote/a.sh", content="ok", is_local=False)
        frame.Show()
        wx.Yield()
        tabs = panel._wx_editor_controls["doc_tabs"]
        assert tabs.GetPageCount() == 1
        panel._wx_editor_load_document("/remote/blob.bin", "ab\x00cd", is_local=False)
        wx.Yield()
        assert tabs.GetPageCount() == 1
        assert "Binary" in panel._wx_editor_controls["status"].GetLabel()
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w26_wx_connection_switch_blocks_remote_save(wx_app):
    from hpc_gui.wx_shell import _editor_action_factory, _editor_session_key

    writes = []

    def make_files():
        return type("F", (), {"write_text": lambda self, p, c: writes.append((p, c))})()

    state = {
        "session": {
            "profile_name": "lab",
            "profile": {"name": "lab", "host": "h1", "port": 22, "username": "u"},
            "files": make_files(),
            "slurm": None,
            "ssh": None,
        }
    }
    factory = _editor_action_factory(state)
    key = _editor_session_key(state)
    assert key
    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(
            frame,
            path="/remote/job.sh",
            content="echo hi",
            is_local=False,
            action_factory=factory,
            session_key=key,
            profile="lab",
        )
        frame.Show()
        wx.Yield()
        # Switch the live connection underneath the open tab.
        state["session"] = {
            "profile_name": "other",
            "profile": {"name": "other", "host": "h2", "port": 22, "username": "u"},
            "files": make_files(),
            "slurm": None,
            "ssh": None,
        }
        controls = panel._wx_editor_controls
        controls["editor"].SetValue("echo changed")
        _click(controls["save"])
        _pump(wx_app, lambda: not panel._wx_editor_state["in_flight"])
        assert writes == []
        assert controls["status"].GetLabel() != ""
        assert panel._wx_editor_model.controller.active.dirty
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w26_wx_save_as_header_redirect_creates_new_target(wx_app, tmp_path):
    source = tmp_path / "orig.sh"
    source.write_text("original", encoding="utf-8")
    target = tmp_path / "copy.sh"
    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(frame, path=str(source), content="original", is_local=True)
        frame.Show()
        wx.Yield()
        header = panel._wx_editor_header["path"]
        header.SetValue(str(target))
        controls = panel._wx_editor_controls
        controls["editor"].SetValue("edited")
        _click(controls["save"])
        _pump(wx_app, lambda: not panel._wx_editor_state["in_flight"])
        assert target.read_bytes() == b"edited"
        assert source.read_text(encoding="utf-8") == "original"
        assert panel._wx_editor_model.controller.active.path == str(target)
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w26_wx_same_path_other_session_opens_distinct_tab(wx_app):
    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(frame, path="/remote/job.sh", content="a", is_local=False, session_key="A")
        frame.Show()
        wx.Yield()
        panel._wx_editor_load_document("/remote/job.sh", "b", is_local=False, session_key="B")
        wx.Yield()
        tabs = panel._wx_editor_controls["doc_tabs"]
        assert tabs.GetPageCount() == 2
    finally:
        _close(frame, wx_app)
